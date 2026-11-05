import React, { useState, useEffect, useRef } from 'react';
import L from 'leaflet';
import { marked } from 'marked';

// Fix Leaflet marker icons
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

marked.setOptions({
  breaks: true,
  gfm: true
});

// Normalize malformed LLM markdown tables (trailing quotes on delimiters, missing closing pipes, missing blank lines)
function normalizeMarkdownTables(md) {
  if (!md || typeof md !== 'string') return md || '';

  const lines = md.split('\n');
  const result = [];
  let inTable = false;
  let tableCols = 0;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();

    // Check if line looks like a table delimiter: e.g. |---|---| or |:---|:---| or |--|--|' or |---|---|`
    const isDelimiter = /^\|?(\s*:?-{2,}:?\s*\|)+\s*:?-{2,}:?\s*\|?['"`\s]*$/.test(trimmed) && trimmed.includes('-');

    if (isDelimiter) {
      let cleanDelim = trimmed.replace(/['"`\s]+$/, '').trim();
      if (!cleanDelim.startsWith('|')) cleanDelim = '| ' + cleanDelim;
      if (!cleanDelim.endsWith('|')) cleanDelim = cleanDelim + ' |';

      tableCols = (cleanDelim.match(/-+/g) || []).length;

      if (result.length > 0) {
        let prev = result[result.length - 1].trim();
        if (prev.startsWith('|')) {
          if (!prev.endsWith('|')) prev = prev + ' |';
          result[result.length - 1] = prev;
        }
        if (result.length > 1 && result[result.length - 2].trim() !== '') {
          result.splice(result.length - 1, 0, '');
        }
      }

      result.push(cleanDelim);
      inTable = true;
      continue;
    }

    if (trimmed.startsWith('|')) {
      let cleanRow = trimmed;
      if (!cleanRow.endsWith('|')) {
        cleanRow = cleanRow + ' |';
      }

      if (inTable && tableCols > 0) {
        const pipeCount = (cleanRow.match(/\|/g) || []).length;
        const cellCount = pipeCount - 1;

        if (cellCount < tableCols) {
          cleanRow = cleanRow + '  |'.repeat(tableCols - cellCount);
        }
      }

      result.push(cleanRow);
      continue;
    }

    if (inTable) {
      inTable = false;
      tableCols = 0;
      if (trimmed !== '') {
        result.push('');
      }
    }
    result.push(line);
  }

  return result.join('\n');
}

const API_BASE = window.location.port === '5173' ? 'http://localhost:8000' : '';

export default function App() {
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      role: 'assistant',
      content: `### Welcome to TerraPulse AIR
I am your autonomous atmospheric science and environmental investigation agent.

Ask me about any city or region, compare criteria pollutants, verify scientific literature, or investigate air pollution causes. Live tool executions and tokens will stream in real time.`,
      statusMessage: null,
      activeTools: [],
      citations: [],
      isStreaming: false,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);

  const [inputPrompt, setInputPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [selectedModel, setSelectedModel] = useState('auto');
  const [availableModels, setAvailableModels] = useState([]);
  const [systemStatus, setSystemStatus] = useState(null);
  const [activeTab, setActiveTab] = useState('chat'); // 'chat', 'sensors', 'pollutants'
  const [activePollutant, setActivePollutant] = useState('PM2.5');
  const [pollutantData, setPollutantData] = useState(null);
  const [searchLocation, setSearchLocation] = useState('Bengaluru');
  const [stations, setStations] = useState([]);
  const [searchingStations, setSearchingStations] = useState(false);
  const [stationMeasurements, setStationMeasurements] = useState(null);
  const [expandedSteps, setExpandedSteps] = useState({});
  const [expandedThinking, setExpandedThinking] = useState({});
  const [copiedId, setCopiedId] = useState(null);

  const messagesEndRef = useRef(null);
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const layerGroupRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  useEffect(() => {
    fetch(`${API_BASE}/api/models`)
      .then(res => res.json())
      .then(data => setAvailableModels(data.models || []))
      .catch(err => console.error('Error fetching models:', err));

    fetch(`${API_BASE}/api/status`)
      .then(res => res.json())
      .then(data => setSystemStatus(data))
      .catch(err => console.error('Error fetching status:', err));
  }, []);

  // Initialize Map
  useEffect(() => {
    if (!mapContainerRef.current) return;
    if (mapInstanceRef.current) return;

    const map = L.map(mapContainerRef.current).setView([12.9716, 77.5946], 6);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    const layerGroup = L.layerGroup().addTo(map);
    mapInstanceRef.current = map;
    layerGroupRef.current = layerGroup;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  useEffect(() => {
    fetch(`${API_BASE}/api/pollutant/${activePollutant}`)
      .then(res => res.json())
      .then(data => setPollutantData(data))
      .catch(err => console.error('Pollutant fetch error:', err));
  }, [activePollutant]);

  const renderMapFeatures = (mapFeatures) => {
    if (!mapFeatures || !mapFeatures.features || mapFeatures.features.length === 0) return;
    if (!mapInstanceRef.current || !layerGroupRef.current) return;

    layerGroupRef.current.clearLayers();
    const geoJsonLayer = L.geoJSON(mapFeatures, {
      pointToLayer: (feature, latlng) => {
        const p = feature.properties || {};
        if (p.feature_type === 'monitoring_station') {
          return L.circleMarker(latlng, {
            radius: 8,
            fillColor: '#2563eb', // Blue
            color: '#1d4ed8',
            weight: 2,
            opacity: 1,
            fillOpacity: 0.85
          });
        } else if (p.feature_type === 'potential_emission_source') {
          return L.circleMarker(latlng, {
            radius: 8,
            fillColor: '#ef4444', // Red
            color: '#b91c1c',
            weight: 2,
            opacity: 1,
            fillOpacity: 0.85
          });
        } else if (p.feature_type === 'reference_location') {
          return L.circleMarker(latlng, {
            radius: 7,
            fillColor: '#10b981', // Emerald
            color: '#047857',
            weight: 2,
            opacity: 1,
            fillOpacity: 0.85
          });
        }
        return L.circleMarker(latlng, { radius: 6, fillColor: '#6b7280', color: '#374151' });
      },
      onEachFeature: (feature, layer) => {
        const p = feature.properties || {};
        let popupHtml = `<div style="font-family: sans-serif; font-size: 13px; color: #1e293b; max-width: 280px;">`;
        if (p.feature_type === 'monitoring_station') {
          popupHtml += `<div style="display:flex; align-items:center; gap:6px; margin-bottom:4px;">
            <span style="display:inline-block; width:10px; height:10px; border-radius:50%; background:#2563eb;"></span>
            <strong style="color:#1d4ed8;">OpenAQ Monitoring Station</strong>
          </div>`;
          popupHtml += `<div><strong>${p.name || 'Station ' + p.id}</strong></div>`;
          popupHtml += `<div style="font-size:11px; color:#64748b; margin-top:2px;">Source: ${p.source_dataset || 'OpenAQ v3 API'}</div>`;
          if (p.measurements && p.measurements.length > 0) {
            popupHtml += `<div style="margin-top:6px; font-weight:600; font-size:11px; border-top:1px solid #e2e8f0; padding-top:4px;">Latest Measurements:</div>`;
            p.measurements.slice(0, 5).forEach(m => {
              popupHtml += `<div style="font-size:11px; color:#334155;">${m.parameter_name || m.parameter}: <strong>${m.value} ${m.units}</strong></div>`;
            });
          }
        } else if (p.feature_type === 'investigation_buffer') {
          popupHtml += `<div style="display:flex; align-items:center; gap:6px; margin-bottom:4px;">
            <span style="display:inline-block; width:10px; height:10px; border-radius:2px; background:#60a5fa; border:1px solid #1d4ed8;"></span>
            <strong style="color:#1d4ed8;">Estimated Investigation Buffer</strong>
          </div>`;
          popupHtml += `<div>Radius: <strong>${p.radius_km} km</strong> (Area: ~${p.area_km2} km²)</div>`;
          popupHtml += `<div style="font-size:11px; color:#b45309; margin-top:4px; font-style:italic; background:#fef3c7; padding:4px; border-radius:4px; border:1px solid #fde68a;">⚠️ Scientific Disclaimer: This is an estimated spatial search buffer for locating sensors and nearby sources, NOT an atmospheric dispersion plume.</div>`;
        } else if (p.feature_type === 'potential_emission_source') {
          popupHtml += `<div style="display:flex; align-items:center; gap:6px; margin-bottom:4px;">
            <span style="display:inline-block; width:10px; height:10px; border-radius:50%; background:#ef4444;"></span>
            <strong style="color:#b91c1c;">Potential Emission Source</strong>
          </div>`;
          popupHtml += `<div><strong>${p.name}</strong></div>`;
          popupHtml += `<div style="font-size:11px; color:#475569;">Type: ${p.source_type}</div>`;
          if (p.distance_km) {
            popupHtml += `<div style="font-size:11px; color:#475569;">Distance: ${p.distance_km} km</div>`;
          }
          popupHtml += `<div style="font-size:10px; color:#64748b; margin-top:4px;">Source: ${p.source_dataset || 'OpenStreetMap Overpass'}</div>`;
        } else {
          popupHtml += `<strong>${p.name || p.label || 'Reference Location'}</strong>`;
          popupHtml += `<div style="font-size:11px; color:#047857; margin-top:2px;">Target Inquiry Coordinates</div>`;
        }
        popupHtml += `</div>`;
        layer.bindPopup(popupHtml);
      },
      style: (feature) => {
        const p = feature.properties || {};
        if (p.feature_type === 'investigation_buffer') {
          return {
            color: '#1d4ed8',
            fillColor: '#60a5fa',
            weight: 2,
            opacity: 0.8,
            fillOpacity: 0.18,
            dashArray: '5, 5'
          };
        }
        return { color: '#ef4444', weight: 2 };
      }
    });

    layerGroupRef.current.addLayer(geoJsonLayer);
    const bounds = geoJsonLayer.getBounds();
    if (bounds.isValid()) {
      mapInstanceRef.current.fitBounds(bounds, { maxZoom: 13, padding: [20, 20] });
    }
  };

  const handleSearchStations = async (locQuery = searchLocation) => {
    if (!locQuery.trim()) return;
    setSearchingStations(true);
    try {
      const geoRes = await fetch(`${API_BASE}/api/geospatial/geocode?location=${encodeURIComponent(locQuery)}`);
      let coords = null;
      if (geoRes.ok) {
        const geoData = await geoRes.json();
        coords = [geoData.latitude, geoData.longitude];
      }

      let url = `${API_BASE}/api/environmental/locations?query=${encodeURIComponent(locQuery)}&limit=10`;
      if (coords) {
        url = `${API_BASE}/api/environmental/locations?latitude=${coords[0]}&longitude=${coords[1]}&radius=40000&limit=10`;
      }

      const res = await fetch(url);
      const data = await res.json();
      setStations(data);

      if (mapInstanceRef.current && layerGroupRef.current) {
        layerGroupRef.current.clearLayers();
        if (coords) {
          mapInstanceRef.current.setView(coords, 10);
        }

        data.forEach(st => {
          if (st.coordinates) {
            const marker = L.marker([st.coordinates.latitude, st.coordinates.longitude]);
            marker.bindPopup(`
              <div style="font-family: sans-serif; font-size: 13px;">
                <strong style="color: #1e40af;">${st.name}</strong><br>
                <span>Sensors: ${st.sensors.length}</span><br>
                <span>ID: ${st.id}</span>
              </div>
            `);
            marker.on('click', () => loadStationDetails(st.id));
            layerGroupRef.current.addLayer(marker);
          }
        });
      }
    } catch (err) {
      console.error('Station search error:', err);
    } finally {
      setSearchingStations(false);
    }
  };

  const loadStationDetails = async (stationId) => {
    try {
      const res = await fetch(`${API_BASE}/api/environmental/station/${stationId}/latest`);
      const data = await res.json();
      setStationMeasurements(data);
    } catch (err) {
      console.error('Station details error:', err);
    }
  };

  // REAL-TIME SERVER-SENT EVENTS (SSE) STREAMING
  const handleSendMessage = async (textToSend = inputPrompt) => {
    if (!textToSend.trim() || loading) return;

    const userMessage = {
      id: `usr_${Date.now()}`,
      role: 'user',
      content: textToSend,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    const assistantMsgId = `ast_${Date.now()}`;
    const initialAssistantMessage = {
      id: assistantMsgId,
      role: 'assistant',
      content: '',
      thinkingContent: '',
      statusMessage: 'Connecting to agent and formulating plan...',
      activeTools: [],
      citations: [],
      isStreaming: true,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages(prev => [...prev, userMessage, initialAssistantMessage]);
    setInputPrompt('');
    setLoading(true);

    try {
      const response = await fetch(`${API_BASE}/api/agent/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: textToSend,
          provider_preference: selectedModel
        })
      });

      if (!response.ok) {
        throw new Error(`Server returned ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop(); // keep last unfinished piece

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed.startsWith('data: ')) continue;

          try {
            const evt = JSON.parse(trimmed.slice(6));

            if (evt.type === 'status') {
              setMessages(prev => prev.map(m =>
                m.id === assistantMsgId ? { ...m, statusMessage: evt.message } : m
              ));
            }

            else if (evt.type === 'tool_start') {
              // Immediately show tool start
              setMessages(prev => prev.map(m => {
                if (m.id !== assistantMsgId) return m;
                const newTool = {
                  id: `tool_${Date.now()}_${Math.random()}`,
                  name: evt.tool_name,
                  arguments: evt.arguments,
                  iteration: evt.iteration,
                  status: 'running'
                };
                return {
                  ...m,
                  statusMessage: `Running tool: ${evt.tool_name}...`,
                  activeTools: [...(m.activeTools || []), newTool]
                };
              }));
            }

            else if (evt.type === 'tool_done') {
              // Immediately update tool completed
              setMessages(prev => prev.map(m => {
                if (m.id !== assistantMsgId) return m;
                const updatedTools = (m.activeTools || []).map(t => {
                  if (t.name === evt.tool_name && t.status === 'running') {
                    return {
                      ...t,
                      status: evt.error ? 'error' : 'completed',
                      duration_ms: evt.duration_ms,
                      preview: evt.preview,
                      data: evt.data
                    };
                  }
                  return t;
                });
                return {
                  ...m,
                  statusMessage: evt.error ? `Error in ${evt.tool_name}` : `✓ ${evt.tool_name} completed in ${evt.duration_ms}ms`,
                  activeTools: updatedTools
                };
              }));
            }

            else if (evt.type === 'map_update') {
              // Immediately update Leaflet map live
              renderMapFeatures(evt.map_features);
            }

            else if (evt.type === 'citations_update') {
              setMessages(prev => prev.map(m =>
                m.id === assistantMsgId ? { ...m, citations: evt.citations } : m
              ));
            }

            else if (evt.type === 'evidence_synthesis') {
              setMessages(prev => prev.map(m =>
                m.id === assistantMsgId ? { ...m, evidenceSynthesis: evt.synthesis } : m
              ));
            }

            else if (evt.type === 'thought_token') {
              // Live individual thinking token streaming from Ollama / Granite
              setMessages(prev => prev.map(m => {
                if (m.id !== assistantMsgId) return m;
                return {
                  ...m,
                  thinkingContent: (m.thinkingContent || '') + evt.content
                };
              }));
            }

            else if (evt.type === 'token') {
              // Live token streaming
              setMessages(prev => prev.map(m => {
                if (m.id !== assistantMsgId) return m;
                return {
                  ...m,
                  statusMessage: null,
                  content: (m.content || '') + evt.content
                };
              }));
            }

            else if (evt.type === 'error') {
              setMessages(prev => prev.map(m => {
                if (m.id !== assistantMsgId) return m;
                return {
                  ...m,
                  isStreaming: false,
                  statusMessage: null,
                  content: (m.content ? m.content + '\n\n' : '') + `⚠️ **Execution Error**: ${evt.error}`
                };
              }));
            }

            else if (evt.type === 'done') {
              // Finalization
              setMessages(prev => prev.map(m => {
                if (m.id !== assistantMsgId) return m;
                return {
                  ...m,
                  isStreaming: false,
                  statusMessage: null,
                  content: evt.final_answer || m.content,
                  citations: evt.citations || m.citations,
                  total_duration_ms: evt.total_duration_ms
                };
              }));
              if (evt.map_features) {
                renderMapFeatures(evt.map_features);
              }
            }

          } catch (jsonErr) {
            console.error('Error parsing SSE event:', jsonErr);
          }
        }
      }

    } catch (err) {
      setMessages(prev => prev.map(m => {
        if (m.id !== assistantMsgId) return m;
        return {
          ...m,
          isStreaming: false,
          statusMessage: null,
          content: `⚠️ **Agent Error**: ${err.message}\n\n*Tip: If cloud quotas or network limits occur, switch to **Ollama Local (granite4.2:3b)** in the AI Model dropdown above to run completely offline without quota limits.*`
        };
      }));
    } finally {
      setLoading(false);
      setMessages(prev => prev.map(m => m.id === assistantMsgId ? { ...m, isStreaming: false } : m));
    }
  };

  const copyToClipboard = (text, id) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const toggleSteps = (id) => {
    setExpandedSteps(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const toggleThinking = (id) => {
    setExpandedThinking(prev => ({ ...prev, [id]: prev[id] === false ? true : false }));
  };

  const suggestedPrompts = [
    "Investigate Bengaluru air quality",
    "Compare PM2.5, PM10, and Ozone",
    "Find 5 peer-reviewed papers on PM2.5 health effects",
    "Investigate unknown pollutant XYZ-927",
    "Create a 2 km investigation buffer for Delhi"
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', width: '100vw', background: '#0b0f19', color: '#f3f4f6', overflow: 'hidden' }}>
      
      {/* Header with Model Switcher & Status */}
      <header style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0.6rem 1.25rem',
        background: '#111827',
        borderBottom: '1px solid #1f2937',
        zIndex: 100
      }}>
        {/* Brand */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{
            width: '32px',
            height: '32px',
            borderRadius: '8px',
            background: 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '18px',
            boxShadow: '0 2px 6px rgba(59, 130, 246, 0.4)'
          }}>
            🌍
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{ fontSize: '1.05rem', fontWeight: '700', color: '#f9fafb', letterSpacing: '-0.3px' }}>
                TerraPulse AIR
              </span>
              <span style={{
                background: '#1e3a8a',
                color: '#93c5fd',
                fontSize: '0.65rem',
                padding: '0.15rem 0.45rem',
                borderRadius: '9999px',
                fontWeight: '600',
                textTransform: 'uppercase'
              }}>
                v2.0 Live Stream
              </span>
            </div>
            <div style={{ fontSize: '0.72rem', color: '#9ca3af' }}>
              Real-time Token &amp; Tool Execution Streaming
            </div>
          </div>
        </div>

        {/* Model Switcher */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', background: '#0f172a', padding: '0.3rem 0.6rem', borderRadius: '8px', border: '1px solid #374151' }}>
          <span style={{ fontSize: '0.75rem', color: '#9ca3af', fontWeight: '500' }}>AI Model:</span>
          <select
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            style={{
              background: 'transparent',
              color: '#60a5fa',
              border: 'none',
              outline: 'none',
              fontSize: '0.82rem',
              fontWeight: '600',
              cursor: 'pointer'
            }}
          >
            <option value="auto" style={{ background: '#111827', color: '#f9fafb' }}>⚡ Auto Failover (Gemini / Ollama)</option>
            <option value="gemini" style={{ background: '#111827', color: '#f9fafb' }}>☁️ Google Gemini Cloud</option>
            <option value="ollama" style={{ background: '#111827', color: '#f9fafb' }}>💻 Ollama Local (granite4.2:3b)</option>
          </select>
          <span style={{
            display: 'inline-block',
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            background: selectedModel === 'ollama' ? '#10b981' : (selectedModel === 'gemini' ? '#3b82f6' : '#a855f7'),
            boxShadow: '0 0 6px currentColor'
          }} />
        </div>

        {/* Status Badges & QA Workbench */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          {systemStatus?.persistence?.fallback_active && (
            <span style={{
              background: '#312e81',
              color: '#c7d2fe',
              fontSize: '0.7rem',
              padding: '0.25rem 0.55rem',
              borderRadius: '6px',
              border: '1px solid #4338ca',
              display: 'flex',
              alignItems: 'center',
              gap: '0.35rem'
            }}>
              💾 SQLite Fallback Active
            </span>
          )}

          <a
            href="/workbench"
            target="_blank"
            rel="noreferrer"
            style={{
              background: 'linear-gradient(135deg, #4f46e5 0%, #4338ca 100%)',
              color: 'white',
              padding: '0.4rem 0.85rem',
              borderRadius: '6px',
              fontSize: '0.8rem',
              fontWeight: '600',
              textDecoration: 'none',
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
              boxShadow: '0 2px 6px rgba(79, 70, 229, 0.3)'
            }}
          >
            🛠️ QA Workbench
          </a>
        </div>
      </header>

      {/* Main Split Pane */}
      <div style={{ display: 'flex', flex: 1, minHeight: 0, overflow: 'hidden' }}>
        
        {/* Left Pane: Real-time ChatGPT-Style Chat Column */}
        <div style={{
          width: '560px',
          minWidth: '440px',
          maxWidth: '680px',
          display: 'flex',
          flexDirection: 'column',
          background: '#0d1117',
          borderRight: '1px solid #21262d',
          minHeight: 0
        }}>
          
          {/* Sub Navigation */}
          <div style={{ display: 'flex', borderBottom: '1px solid #21262d', background: '#161b22' }}>
            <button
              onClick={() => setActiveTab('chat')}
              style={{
                flex: 1,
                padding: '0.65rem 0',
                background: activeTab === 'chat' ? '#0d1117' : 'transparent',
                color: activeTab === 'chat' ? '#58a6ff' : '#8b949e',
                border: 'none',
                borderBottom: activeTab === 'chat' ? '2px solid #58a6ff' : '2px solid transparent',
                fontWeight: '600',
                fontSize: '0.82rem',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '0.35rem'
              }}
            >
              💬 Live Stream Chat
            </button>
            <button
              onClick={() => setActiveTab('sensors')}
              style={{
                flex: 1,
                padding: '0.65rem 0',
                background: activeTab === 'sensors' ? '#0d1117' : 'transparent',
                color: activeTab === 'sensors' ? '#58a6ff' : '#8b949e',
                border: 'none',
                borderBottom: activeTab === 'sensors' ? '2px solid #58a6ff' : '2px solid transparent',
                fontWeight: '600',
                fontSize: '0.82rem',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '0.35rem'
              }}
            >
              📡 OpenAQ Stations
            </button>
            <button
              onClick={() => setActiveTab('pollutants')}
              style={{
                flex: 1,
                padding: '0.65rem 0',
                background: activeTab === 'pollutants' ? '#0d1117' : 'transparent',
                color: activeTab === 'pollutants' ? '#58a6ff' : '#8b949e',
                border: 'none',
                borderBottom: activeTab === 'pollutants' ? '2px solid #58a6ff' : '2px solid transparent',
                fontWeight: '600',
                fontSize: '0.82rem',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '0.35rem'
              }}
            >
              📊 Pollutant Intel
            </button>
          </div>

          {/* TAB 1: LIVE CHAT */}
          {activeTab === 'chat' && (
            <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
              
              {/* Messages Container with Smooth Scrolling */}
              <div style={{
                flex: 1,
                overflowY: 'auto',
                padding: '1.25rem 1rem',
                display: 'flex',
                flexDirection: 'column',
                gap: '1.25rem',
                minHeight: 0
              }}>
                {messages.map((msg) => (
                  <div
                    key={msg.id}
                    style={{
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: msg.role === 'user' ? 'flex-end' : 'flex-start',
                      maxWidth: '100%'
                    }}
                  >
                    {/* Header */}
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.4rem',
                      marginBottom: '0.25rem',
                      fontSize: '0.75rem',
                      color: '#8b949e'
                    }}>
                      <span>{msg.role === 'user' ? 'You' : 'TerraPulse AIR'}</span>
                      <span>&bull;</span>
                      <span>{msg.timestamp}</span>
                    </div>

                    {/* Bubble */}
                    <div style={{
                      maxWidth: msg.role === 'user' ? '85%' : '100%',
                      width: msg.role === 'user' ? 'auto' : '100%',
                      background: msg.role === 'user' ? '#1f6feb' : '#161b22',
                      color: '#f0f6fc',
                      padding: '0.85rem 1rem',
                      borderRadius: msg.role === 'user' ? '14px 14px 2px 14px' : '14px 14px 14px 2px',
                      border: msg.role === 'user' ? 'none' : '1px solid #30363d',
                      boxShadow: '0 2px 8px rgba(0,0,0,0.25)'
                    }}>
                      
                      {/* REAL-TIME LIVE AGENT REASONING / THINKING STREAM (ChatGPT/Antigravity style) */}
                      {msg.role === 'assistant' && msg.thinkingContent && (
                        <div style={{
                          marginBottom: '0.75rem',
                          background: '#0d1117',
                          border: '1px solid #30363d',
                          borderRadius: '8px',
                          overflow: 'hidden'
                        }}>
                          <div
                            onClick={() => toggleThinking(msg.id)}
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'space-between',
                              padding: '0.45rem 0.75rem',
                              background: '#161b22',
                              cursor: 'pointer',
                              fontSize: '0.76rem',
                              userSelect: 'none'
                            }}
                          >
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', color: '#a5d6ff' }}>
                              <span>🧠</span>
                              <strong>
                                {msg.isStreaming && !msg.content
                                  ? 'Live Model Reasoning & Thought Trace...'
                                  : 'Model Reasoning & Thought Trace'}
                              </strong>
                              {msg.isStreaming && !msg.content && (
                                <span style={{
                                  display: 'inline-block',
                                  width: '7px',
                                  height: '7px',
                                  borderRadius: '50%',
                                  background: '#3fb950',
                                  animation: 'pulse 1.5s infinite'
                                }} />
                              )}
                            </div>
                            <span style={{ color: '#8b949e', fontSize: '0.7rem' }}>
                              {expandedThinking[msg.id] === false ? 'Show Thoughts ▼' : 'Hide Thoughts ▲'}
                            </span>
                          </div>

                          {expandedThinking[msg.id] !== false && (
                            <div style={{
                              padding: '0.65rem 0.75rem',
                              fontSize: '0.76rem',
                              lineHeight: '1.45',
                              color: '#c9d1d9',
                              fontFamily: 'Consolas, Monaco, monospace',
                              whiteSpace: 'pre-wrap',
                              wordBreak: 'break-word',
                              maxHeight: '260px',
                              overflowY: 'auto',
                              borderTop: '1px solid #21262d',
                              background: '#0a0d12'
                            }}>
                              {msg.thinkingContent}
                              {msg.isStreaming && !msg.content && (
                                <span style={{
                                  display: 'inline-block',
                                  width: '7px',
                                  height: '13px',
                                  background: '#58a6ff',
                                  marginLeft: '3px',
                                  verticalAlign: 'middle',
                                  animation: 'blink 1s step-start infinite'
                                }} />
                              )}
                            </div>
                          )}
                        </div>
                      )}

                      {/* REAL-TIME LIVE TOOL PILLS (ChatGPT/Antigravity style) */}
                      {msg.role === 'assistant' && msg.activeTools && msg.activeTools.length > 0 && (
                        <div style={{ marginBottom: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                            <span style={{ fontSize: '0.75rem', fontWeight: '600', color: '#58a6ff' }}>
                              ⚡ Agentic Tools Executed ({msg.activeTools.length}):
                            </span>
                            <button
                              onClick={() => toggleSteps(msg.id)}
                              style={{ background: 'transparent', border: 'none', color: '#8b949e', fontSize: '0.7rem', cursor: 'pointer' }}
                            >
                              {expandedSteps[msg.id] ? 'Hide Details ▲' : 'Show Details ▼'}
                            </button>
                          </div>

                          {/* Pill Badges */}
                          <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
                            {msg.activeTools.map((t, tIdx) => (
                              <div
                                key={t.id || tIdx}
                                style={{
                                  display: 'flex',
                                  alignItems: 'center',
                                  gap: '0.35rem',
                                  padding: '0.25rem 0.55rem',
                                  borderRadius: '6px',
                                  fontSize: '0.74rem',
                                  background: t.status === 'running' ? '#1c1917' : '#0d1117',
                                  border: t.status === 'running' ? '1px solid #d97706' : (t.status === 'error' ? '1px solid #b91c1c' : '1px solid #238636'),
                                  color: t.status === 'running' ? '#f59e0b' : (t.status === 'error' ? '#f87171' : '#7ee787')
                                }}
                              >
                                <span>{t.status === 'running' ? '⏳' : (t.status === 'error' ? '❌' : '✓')}</span>
                                <strong>{t.name}</strong>
                                {t.duration_ms && <span style={{ color: '#8b949e' }}>({t.duration_ms}ms)</span>}
                              </div>
                            ))}
                          </div>

                          {/* Expanded Step Inspector */}
                          {expandedSteps[msg.id] && (
                            <div style={{ background: '#0d1117', border: '1px solid #30363d', borderRadius: '6px', padding: '0.5rem', marginTop: '0.35rem', fontSize: '0.74rem', display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                              {msg.activeTools.map((t, idx) => (
                                <div key={idx} style={{ borderBottom: '1px solid #21262d', paddingBottom: '0.3rem' }}>
                                  <div style={{ color: '#79c0ff', fontWeight: '600' }}>{t.name} &bull; {t.duration_ms ? `${t.duration_ms}ms` : 'running'}</div>
                                  <div style={{ color: '#8b949e' }}>Args: <code style={{ color: '#a5d6ff' }}>{JSON.stringify(t.arguments)}</code></div>
                                  {t.preview && <div style={{ color: '#7ee787' }}>Observation: {t.preview}</div>}
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}

                      {/* EVIDENCE SYNTHESIS & HYPOTHESES CARD */}
                      {msg.role === 'assistant' && msg.evidenceSynthesis && (
                        <div style={{
                          marginBottom: '0.85rem',
                          background: '#0d1117',
                          border: '1px solid #30363d',
                          borderRadius: '8px',
                          padding: '0.65rem 0.85rem',
                          fontSize: '0.76rem'
                        }}>
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.45rem' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontWeight: '600', color: '#a5d6ff' }}>
                              <span>🔬</span>
                              <span>Evidence Synthesis &amp; Hypotheses Matrix</span>
                            </div>
                            <span style={{
                              padding: '0.15rem 0.45rem',
                              borderRadius: '4px',
                              fontSize: '0.68rem',
                              fontWeight: '600',
                              background: msg.evidenceSynthesis.stopping_recommendation === 'SUFFICIENT_EVIDENCE_FOR_FINAL' ? '#064e3b' : (msg.evidenceSynthesis.stopping_recommendation === 'INCONCLUSIVE_NO_STATIONS' ? '#78350f' : '#1e293b'),
                              color: msg.evidenceSynthesis.stopping_recommendation === 'SUFFICIENT_EVIDENCE_FOR_FINAL' ? '#6ee7b7' : (msg.evidenceSynthesis.stopping_recommendation === 'INCONCLUSIVE_NO_STATIONS' ? '#fde68a' : '#93c5fd'),
                              border: '1px solid ' + (msg.evidenceSynthesis.stopping_recommendation === 'SUFFICIENT_EVIDENCE_FOR_FINAL' ? '#047857' : (msg.evidenceSynthesis.stopping_recommendation === 'INCONCLUSIVE_NO_STATIONS' ? '#b45309' : '#3b82f6'))
                            }}>
                              {msg.evidenceSynthesis.stopping_recommendation === 'SUFFICIENT_EVIDENCE_FOR_FINAL' ? '✓ Sufficient Evidence' : (msg.evidenceSynthesis.stopping_recommendation === 'INCONCLUSIVE_NO_STATIONS' ? '⚠️ Inconclusive (No Stations)' : '🔍 Investigating')}
                            </span>
                          </div>

                          {/* Quick Stats Bar */}
                          <div style={{ display: 'flex', gap: '0.6rem', flexWrap: 'wrap', marginBottom: '0.5rem', color: '#8b949e', fontSize: '0.72rem' }}>
                            <span>Target: <strong style={{ color: '#f0f6fc' }}>{msg.evidenceSynthesis.target_location || 'Resolving...'}</strong></span>
                            <span>&bull;</span>
                            <span>Stations: <strong style={{ color: '#58a6ff' }}>{msg.evidenceSynthesis.stations_count}</strong></span>
                            <span>&bull;</span>
                            <span>Measurements: <strong style={{ color: '#3fb950' }}>{msg.evidenceSynthesis.measurements_retrieved}</strong></span>
                            {msg.evidenceSynthesis.pollutants_detected && msg.evidenceSynthesis.pollutants_detected.length > 0 && (
                              <>
                                <span>&bull;</span>
                                <span>Pollutants: <strong style={{ color: '#e3b341' }}>{msg.evidenceSynthesis.pollutants_detected.join(', ')}</strong></span>
                              </>
                            )}
                          </div>

                          {/* Hypotheses Matrix */}
                          {msg.evidenceSynthesis.hypotheses && (
                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: '0.4rem', marginTop: '0.4rem' }}>
                              {Object.entries(msg.evidenceSynthesis.hypotheses).map(([k, hyp]) => (
                                <div key={k} style={{ background: '#161b22', border: '1px solid #21262d', borderRadius: '6px', padding: '0.45rem' }}>
                                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.2rem' }}>
                                    <strong style={{ color: '#c9d1d9', fontSize: '0.72rem' }}>{hyp.hypothesis}</strong>
                                    <span style={{
                                      fontSize: '0.62rem',
                                      fontWeight: '600',
                                      padding: '0.1rem 0.35rem',
                                      borderRadius: '3px',
                                      background: hyp.status === 'SUPPORTED' ? '#064e3b' : (hyp.status === 'NO_PROXIMATE_FACILITIES_FOUND' ? '#374151' : '#1e293b'),
                                      color: hyp.status === 'SUPPORTED' ? '#34d399' : (hyp.status === 'NO_PROXIMATE_FACILITIES_FOUND' ? '#9ca3af' : '#60a5fa')
                                    }}>
                                      {hyp.status.replace(/_/g, ' ')}
                                    </span>
                                  </div>
                                  <div style={{ color: '#8b949e', fontSize: '0.68rem', lineHeight: '1.3' }}>{hyp.evidence}</div>
                                </div>
                              ))}
                            </div>
                          )}

                          {/* Missing Evidence */}
                          {msg.evidenceSynthesis.missing_evidence && msg.evidenceSynthesis.missing_evidence.length > 0 && (
                            <div style={{ marginTop: '0.45rem', color: '#f59e0b', fontSize: '0.7rem' }}>
                              ⚠️ Pending evidence: {msg.evidenceSynthesis.missing_evidence.join(' • ')}
                            </div>
                          )}
                        </div>
                      )}

                      {/* Live Status Message (e.g. "Connecting to OpenAQ...", "Querying Crossref...") */}
                      {msg.statusMessage && (
                        <div style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '0.4rem',
                          color: '#58a6ff',
                          fontSize: '0.78rem',
                          marginBottom: '0.5rem',
                          fontStyle: 'italic'
                        }}>
                          <span style={{ display: 'inline-block', animation: 'spin 1s linear infinite' }}>⚙️</span>
                          <span>{msg.statusMessage}</span>
                        </div>
                      )}

                      {/* Live Streamed Token Content */}
                      <div className="chat-prose">
                        {msg.content ? (
                          <div dangerouslySetInnerHTML={{ __html: marked.parse(normalizeMarkdownTables(msg.content)) }} />
                        ) : (
                          msg.isStreaming && <span style={{ color: '#8b949e', fontSize: '0.8rem' }}>Formulating response...</span>
                        )}
                        {/* Blinking cursor while streaming */}
                        {msg.isStreaming && (
                          <span style={{
                            display: 'inline-block',
                            width: '8px',
                            height: '14px',
                            background: '#58a6ff',
                            marginLeft: '4px',
                            verticalAlign: 'middle',
                            animation: 'blink 1s step-start infinite'
                          }} />
                        )}
                      </div>

                      {/* Citations */}
                      {msg.citations && msg.citations.length > 0 && (
                        <div style={{ marginTop: '0.85rem', paddingTop: '0.65rem', borderTop: '1px solid #30363d', fontSize: '0.78rem' }}>
                          <div style={{ fontWeight: '600', color: '#7ee787', marginBottom: '0.35rem' }}>
                            📚 Verified Scholarly Evidence (Crossref Registry):
                          </div>
                          <ul style={{ paddingLeft: '1.2rem', margin: 0, color: '#8b949e' }}>
                            {msg.citations.map((c, idx) => (
                              <li key={idx} style={{ marginBottom: '0.2rem' }}>
                                <strong style={{ color: '#c9d1d9' }}>{c.title}</strong> ({c.year || 'n.d.'}) &mdash;{' '}
                                {c.doi && (
                                  <a href={`https://doi.org/${c.doi}`} target="_blank" rel="noreferrer" style={{ color: '#58a6ff', textDecoration: 'none' }}>
                                    DOI: {c.doi}
                                  </a>
                                )}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Copy Action */}
                      {msg.role === 'assistant' && !msg.isStreaming && (
                        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '0.6rem' }}>
                          <button
                            onClick={() => copyToClipboard(msg.content, msg.id)}
                            style={{ background: 'transparent', border: 'none', color: copiedId === msg.id ? '#3fb950' : '#8b949e', fontSize: '0.72rem', cursor: 'pointer' }}
                          >
                            {copiedId === msg.id ? '✓ Copied' : '📋 Copy text'}
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                ))}

                <div ref={messagesEndRef} />
              </div>

              {/* Suggested Prompts */}
              {messages.length <= 2 && (
                <div style={{ padding: '0 1rem 0.5rem', display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
                  {suggestedPrompts.map((p, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleSendMessage(p)}
                      style={{
                        background: '#161b22',
                        border: '1px solid #30363d',
                        color: '#c9d1d9',
                        padding: '0.3rem 0.65rem',
                        borderRadius: '9999px',
                        fontSize: '0.72rem',
                        cursor: 'pointer'
                      }}
                    >
                      {p}
                    </button>
                  ))}
                </div>
              )}

              {/* Chat Input Bar */}
              <div style={{ padding: '0.85rem 1rem', borderTop: '1px solid #21262d', background: '#161b22', display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'flex-end' }}>
                  <textarea
                    rows={2}
                    value={inputPrompt}
                    onChange={(e) => setInputPrompt(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        handleSendMessage();
                      }
                    }}
                    placeholder="Ask TerraPulse (e.g., Investigate Bengaluru NO2 and PM2.5)..."
                    style={{
                      flex: 1,
                      background: '#0d1117',
                      border: '1px solid #30363d',
                      borderRadius: '8px',
                      color: '#f0f6fc',
                      padding: '0.6rem 0.85rem',
                      fontSize: '0.86rem',
                      resize: 'none',
                      outline: 'none',
                      fontFamily: 'inherit',
                      lineHeight: '1.4'
                    }}
                  />
                  <button
                    onClick={() => handleSendMessage()}
                    disabled={loading || !inputPrompt.trim()}
                    style={{
                      height: '46px',
                      padding: '0 1.25rem',
                      background: inputPrompt.trim() && !loading ? '#238636' : '#21262d',
                      color: inputPrompt.trim() && !loading ? '#ffffff' : '#484f58',
                      border: 'none',
                      borderRadius: '8px',
                      fontWeight: '600',
                      cursor: inputPrompt.trim() && !loading ? 'pointer' : 'not-allowed',
                      fontSize: '0.85rem',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.35rem'
                    }}
                  >
                    <span>{loading ? 'Streaming...' : 'Send'}</span>
                    <span>➔</span>
                  </button>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: '#8b949e' }}>
                  <span>Live Streaming: <strong style={{ color: '#3fb950' }}>Active (Tokens &amp; Tools)</strong></span>
                  <span>Model: <strong style={{ color: '#58a6ff' }}>{selectedModel}</strong></span>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: OPENAQ STATIONS */}
          {activeTab === 'sensors' && (
            <div style={{ flex: 1, overflowY: 'auto', padding: '1rem', minHeight: 0 }}>
              <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
                <input
                  type="text"
                  value={searchLocation}
                  onChange={(e) => setSearchLocation(e.target.value)}
                  placeholder="Enter location (e.g. Bengaluru, Delhi)..."
                  style={{ flex: 1, background: '#0d1117', border: '1px solid #30363d', color: '#f0f6fc', padding: '0.5rem 0.75rem', borderRadius: '6px', fontSize: '0.85rem' }}
                />
                <button
                  onClick={() => handleSearchStations()}
                  disabled={searchingStations}
                  style={{ background: '#1f6feb', color: 'white', border: 'none', padding: '0.5rem 1rem', borderRadius: '6px', fontSize: '0.85rem', fontWeight: '600', cursor: 'pointer' }}
                >
                  {searchingStations ? 'Searching...' : 'Search'}
                </button>
              </div>

              <h4 style={{ fontSize: '0.82rem', color: '#8b949e', marginBottom: '0.5rem', textTransform: 'uppercase' }}>
                Found {stations.length} Station(s):
              </h4>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {stations.map(st => (
                  <div
                    key={st.id}
                    onClick={() => loadStationDetails(st.id)}
                    style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '6px', padding: '0.65rem 0.85rem', cursor: 'pointer' }}
                  >
                    <div style={{ fontWeight: '600', fontSize: '0.85rem', color: '#58a6ff' }}>{st.name}</div>
                    <div style={{ fontSize: '0.74rem', color: '#8b949e', marginTop: '0.2rem' }}>
                      ID: {st.id} &bull; Attached Sensors: {st.sensors.length} &bull; Timezone: {st.timezone || 'UTC'}
                    </div>
                  </div>
                ))}
              </div>

              {stationMeasurements && (
                <div style={{ marginTop: '1.25rem', background: '#161b22', border: '1px solid #30363d', borderRadius: '8px', padding: '0.85rem' }}>
                  <h4 style={{ fontSize: '0.85rem', color: '#7ee787', marginBottom: '0.5rem' }}>
                    Latest Sensor Readings ({stationMeasurements.station_name}):
                  </h4>
                  {stationMeasurements.measurements.length === 0 ? (
                    <p style={{ fontSize: '0.78rem', color: '#8b949e' }}>No recent measurements recorded.</p>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                      {stationMeasurements.measurements.map((m, idx) => (
                        <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', borderBottom: '1px solid #21262d', paddingBottom: '0.25rem' }}>
                          <span style={{ fontWeight: '600', color: '#f0f6fc', textTransform: 'uppercase' }}>{m.parameter_name}:</span>
                          <span style={{ color: '#79c0ff' }}>
                            {m.value} {m.units} {m.is_stale && <span style={{ color: '#d29922' }}>(stale: {m.stale_hours}h)</span>}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* TAB 3: POLLUTANTS INTEL */}
          {activeTab === 'pollutants' && (
            <div style={{ flex: 1, overflowY: 'auto', padding: '1rem', minHeight: 0 }}>
              <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
                {['PM2.5', 'PM10', 'NO2', 'SO2', 'CO', 'O3'].map(code => (
                  <button
                    key={code}
                    onClick={() => setActivePollutant(code)}
                    style={{
                      background: activePollutant === code ? '#1f6feb' : '#161b22',
                      color: activePollutant === code ? '#ffffff' : '#8b949e',
                      border: '1px solid #30363d',
                      padding: '0.35rem 0.75rem',
                      borderRadius: '6px',
                      fontSize: '0.8rem',
                      fontWeight: '600',
                      cursor: 'pointer'
                    }}
                  >
                    {code}
                  </button>
                ))}
              </div>

              {pollutantData && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem', fontSize: '0.82rem', color: '#c9d1d9' }}>
                  <div style={{ borderBottom: '1px solid #30363d', paddingBottom: '0.5rem' }}>
                    <h3 style={{ fontSize: '1.05rem', color: '#58a6ff', fontWeight: '600' }}>{pollutantData.full_name}</h3>
                    <span style={{ fontSize: '0.72rem', background: '#21262d', color: '#a5d6ff', padding: '0.15rem 0.45rem', borderRadius: '4px' }}>
                      Type: {pollutantData.pollutant_type}
                    </span>
                  </div>

                  <p style={{ lineHeight: '1.5' }}>{pollutantData.physical_chemical_characteristics}</p>

                  <div>
                    <strong style={{ color: '#f0f6fc', display: 'block', marginBottom: '0.25rem' }}>Major Emission Sources:</strong>
                    <ul style={{ paddingLeft: '1.2rem', color: '#8b949e' }}>
                      {pollutantData.major_anthropogenic_sources.map((s, idx) => (
                        <li key={idx} style={{ marginBottom: '0.2rem' }}>{s}</li>
                      ))}
                    </ul>
                  </div>

                  <div>
                    <strong style={{ color: '#f85149', display: 'block', marginBottom: '0.25rem' }}>Health Effects (WHO Context):</strong>
                    <ul style={{ paddingLeft: '1.2rem', color: '#8b949e' }}>
                      {pollutantData.health_effects.short_term.slice(0, 3).map((e, idx) => (
                        <li key={idx} style={{ marginBottom: '0.2rem' }}>{e}</li>
                      ))}
                    </ul>
                  </div>

                  <div style={{ background: '#1c1917', border: '1px solid #78350f', padding: '0.6rem', borderRadius: '6px', fontSize: '0.74rem', color: '#fbbf24' }}>
                    ⚠️ {pollutantData.health_effects.medical_disclaimer}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right Pane: Map */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', position: 'relative', height: '100%', minHeight: 0 }}>
          <div ref={mapContainerRef} style={{ flex: 1, width: '100%', height: '100%' }} />
        </div>

      </div>
    </div>
  );
}
