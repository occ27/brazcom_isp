import React, { useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';
import L from 'leaflet';
import { MapContainer, TileLayer, Marker, Popup, useMapEvents, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { useCompany } from '../contexts/CompanyContext';
import { useAuth } from '../contexts/AuthContext';
import * as authService from '../services/authService';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// ============================================================
// COMPONENTES AUXILIARES MAPA
// ============================================================
const ChangeMapCenter: React.FC<{ center: [number, number]; zoom: number }> = ({ center, zoom }) => {
  const map = useMap();
  useEffect(() => {
    map.setView(center, zoom);
  }, [center, zoom, map]);
  return null;
};

const MapClickEvents: React.FC<{ onClick: (latlng: L.LatLng) => void }> = ({ onClick }) => {
  useMapEvents({
    click(e) {
      onClick(e.latlng);
    }
  });
  return null;
};

// ============================================================
// TIPOS
// ============================================================
interface ONUStatus {
  contrato_id: number;
  cliente_nome: string;
  numero_contrato?: string;
  endereco_instalacao?: string;
  onu_serial?: string;
  onu_modelo?: string;
  olt_nome?: string;
  olt_pon?: string;
  cto_nome?: string;
  cto_porta?: string;
  assigned_ip?: string;
  pppoe_username?: string;
  coordenadas_gps?: string;
  vlan_id?: number;
  tipo_conexao?: string;
  status: 'ONLINE' | 'OFFLINE' | 'DEGRADADO' | 'DESCONHECIDO';
  latencia_ms?: number;
  rx_power?: number;
  tx_power?: number;
  is_reachable?: boolean;
  ultima_verificacao?: string;
}

interface Dashboard {
  total_onus: number;
  onus_online: number;
  onus_offline: number;
  onus_degradado: number;
  onus_desconhecido: number;
  disponibilidade_percentual: number;
  total_olts: number;
  total_ctos: number;
  ultima_atualizacao?: string;
}

interface OLT {
  id: number;
  nome: string;
  ip: string;
  porta_snmp: number;
  community_read?: string;
  fabricante?: string;
  modelo?: string;
  firmware?: string;
  localizacao?: string;
  descricao?: string;
  is_active: boolean;
}

interface CTO {
  id: number;
  nome: string;
  olt_id?: number;
  olt_nome?: string;
  porta_pon?: string;
  splitter_ratio?: string;
  capacidade?: number;
  coordenadas_gps?: string;
  endereco?: string;
  descricao?: string;
  is_active: boolean;
}

interface Snapshot {
  id: number;
  timestamp: string;
  status: string;
  latencia_ms?: number;
  rx_power?: number;
  tx_power?: number;
  is_reachable?: boolean;
}

// ============================================================
// HELPERS / CONSTANTES
// ============================================================
const STATUS_CONFIG = {
  ONLINE:       { label: 'Online',       color: '#10b981', bg: '#d1fae5', icon: '🟢' },
  OFFLINE:      { label: 'Offline',      color: '#ef4444', bg: '#fee2e2', icon: '🔴' },
  DEGRADADO:    { label: 'Degradado',    color: '#f59e0b', bg: '#fef3c7', icon: '🟡' },
  DESCONHECIDO: { label: 'Desconhecido', color: '#6b7280', bg: '#f3f4f6', icon: '⚪' },
};

const getAuthHeaders = (token: string, empresaId?: number) => ({
  Authorization: `Bearer ${token}`,
  ...(empresaId ? { 'X-Active-Empresa': String(empresaId) } : {}),
});

function formatDate(iso?: string) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('pt-BR', { timeZone: 'America/Sao_Paulo' });
}

function formatLatency(ms?: number) {
  if (ms == null) return '—';
  return `${ms.toFixed(1)} ms`;
}

function formatPower(dbm?: number) {
  if (dbm == null) return '—';
  return `${dbm.toFixed(1)} dBm`;
}

function parseCoords(coordsStr?: string): [number, number] | null {
  if (!coordsStr) return null;
  const parts = coordsStr.split(',');
  if (parts.length === 2) {
    const lat = parseFloat(parts[0].trim());
    const lng = parseFloat(parts[1].trim());
    if (!isNaN(lat) && !isNaN(lng)) {
      return [lat, lng];
    }
  }
  return null;
}

// ============================================================
// SUB-COMPONENTES
// ============================================================

/** Badge de status colorido */
const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const cfg = STATUS_CONFIG[status as keyof typeof STATUS_CONFIG] || STATUS_CONFIG.DESCONHECIDO;
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      padding: '3px 10px', borderRadius: 999,
      backgroundColor: cfg.bg, color: cfg.color,
      fontWeight: 700, fontSize: 12, letterSpacing: 0.3,
      border: `1px solid ${cfg.color}33`,
    }}>
      {cfg.icon} {cfg.label}
    </span>
  );
};

/** Card de KPI */
const KPICard: React.FC<{
  label: string; value: number | string; sub?: string;
  color?: string; icon: string; bg?: string;
}> = ({ label, value, sub, color = '#4f46e5', icon, bg = '#eef2ff' }) => (
  <div style={{
    background: '#fff', borderRadius: 16, padding: '20px 24px',
    boxShadow: '0 2px 12px rgba(0,0,0,0.07)',
    display: 'flex', alignItems: 'center', gap: 16,
    border: `1px solid ${color}22`,
  }}>
    <div style={{
      width: 52, height: 52, borderRadius: 14, background: bg,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontSize: 24, flexShrink: 0,
    }}>
      {icon}
    </div>
    <div>
      <div style={{ fontSize: 28, fontWeight: 800, color, lineHeight: 1.1 }}>{value}</div>
      <div style={{ fontSize: 13, color: '#6b7280', fontWeight: 600 }}>{label}</div>
      {sub && <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 2 }}>{sub}</div>}
    </div>
  </div>
);

/** Mini gráfico de disponibilidade (sparkline SVG) */
const MiniChart: React.FC<{ snapshots: Snapshot[] }> = ({ snapshots }) => {
  if (!snapshots.length) return <div style={{ color: '#9ca3af', fontSize: 12 }}>Sem dados</div>;
  const w = 280, h = 60;
  const n = Math.min(snapshots.length, 48);
  const recent = snapshots.slice(-n);
  const stepX = w / (n - 1 || 1);

  const points = recent.map((s, i) => {
    const y = s.status === 'ONLINE' ? h * 0.15 : s.status === 'DEGRADADO' ? h * 0.5 : h * 0.85;
    return { x: i * stepX, y };
  });

  const polyline = points.map(p => `${p.x},${p.y}`).join(' ');

  return (
    <svg width={w} height={h} style={{ display: 'block' }}>
      <defs>
        <linearGradient id="spark-grad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#10b981" stopOpacity="0.3" />
          <stop offset="100%" stopColor="#10b981" stopOpacity="0" />
        </linearGradient>
      </defs>
      <polyline points={polyline} fill="none" stroke="#10b981" strokeWidth={2} strokeLinejoin="round" />
      {points.map((p, i) => (
        <circle key={i} cx={p.x} cy={p.y} r={2.5}
          fill={recent[i].status === 'ONLINE' ? '#10b981' : recent[i].status === 'DEGRADADO' ? '#f59e0b' : '#ef4444'}
        />
      ))}
    </svg>
  );
};

// ============================================================
// MODAIS
// ============================================================

/** Modal de Detalhes da ONU */
const ONUDetailModal: React.FC<{
  onu: ONUStatus; onClose: () => void;
  token: string; empresaId?: number;
}> = ({ onu, onClose, token, empresaId }) => {
  const [history, setHistory] = useState<Snapshot[]>([]);
  const [loading, setLoading] = useState(true);
  const [pinging, setPinging] = useState(false);
  const [pingResult, setPingResult] = useState<any>(null);

  useEffect(() => {
    axios.get(`${API_BASE}/ftth/onts/${onu.contrato_id}/historico?horas=24`, {
      headers: getAuthHeaders(token, empresaId),
    }).then(r => setHistory(r.data)).catch(() => {}).finally(() => setLoading(false));
  }, [onu.contrato_id, token, empresaId]);

  const handlePing = async () => {
    setPinging(true);
    setPingResult(null);
    try {
      const r = await axios.post(`${API_BASE}/ftth/onts/${onu.contrato_id}/ping`, {}, {
        headers: getAuthHeaders(token, empresaId),
      });
      setPingResult(r.data);
    } catch (e: any) {
      setPingResult({ error: e.response?.data?.detail || 'Erro ao executar ping' });
    } finally {
      setPinging(false);
    }
  };

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 1000,
      background: 'rgba(0,0,0,0.55)', display: 'flex',
      alignItems: 'center', justifyContent: 'center', padding: 20,
    }} onClick={onClose}>
      <div style={{
        background: '#fff', borderRadius: 20, padding: 32,
        maxWidth: 680, width: '100%', maxHeight: '90vh', overflow: 'auto',
        boxShadow: '0 24px 64px rgba(0,0,0,0.2)',
      }} onClick={e => e.stopPropagation()}>

        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24 }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 4 }}>
              <StatusBadge status={onu.status} />
              <span style={{ fontSize: 11, color: '#9ca3af' }}>Contrato #{onu.contrato_id}</span>
            </div>
            <h2 style={{ fontSize: 20, fontWeight: 800, color: '#111827', margin: 0 }}>{onu.cliente_nome}</h2>
            {onu.numero_contrato && <div style={{ fontSize: 13, color: '#6b7280' }}>Contrato: {onu.numero_contrato}</div>}
          </div>
          <button onClick={onClose} style={{
            background: '#f3f4f6', border: 'none', borderRadius: 8,
            width: 36, height: 36, cursor: 'pointer', fontSize: 18, color: '#6b7280',
          }}>✕</button>
        </div>

        {/* Info Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 24 }}>
          {[
            ['ONU Serial', onu.onu_serial],
            ['Modelo ONU', onu.onu_modelo],
            ['OLT / Porta', onu.olt_nome ? `${onu.olt_nome} / ${onu.olt_pon || '—'}` : null],
            ['CTO / Porta', onu.cto_nome ? `${onu.cto_nome} / ${onu.cto_porta || '—'}` : null],
            ['IP Atribuído', onu.assigned_ip],
            ['VLAN', onu.vlan_id],
            ['Latência', formatLatency(onu.latencia_ms)],
            ['Rx Power', formatPower(onu.rx_power)],
            ['Última verificação', formatDate(onu.ultima_verificacao)],
            ['Endereço', onu.endereco_instalacao],
          ].filter(([, v]) => v != null).map(([label, value]) => (
            <div key={String(label)} style={{
              background: '#f9fafb', borderRadius: 10, padding: '10px 14px',
              border: '1px solid #e5e7eb',
            }}>
              <div style={{ fontSize: 11, color: '#9ca3af', fontWeight: 600, marginBottom: 2 }}>{label}</div>
              <div style={{ fontSize: 14, color: '#111827', fontWeight: 600 }}>{String(value)}</div>
            </div>
          ))}
        </div>

        {/* Ping Manual */}
        <div style={{ marginBottom: 24 }}>
          <button onClick={handlePing} disabled={pinging || (!onu.assigned_ip && !onu.pppoe_username)} style={{
            background: '#4f46e5', color: '#fff', border: 'none', borderRadius: 10,
            padding: '10px 20px', cursor: pinging || (!onu.assigned_ip && !onu.pppoe_username) ? 'not-allowed' : 'pointer',
            fontWeight: 700, fontSize: 14, opacity: pinging || (!onu.assigned_ip && !onu.pppoe_username) ? 0.6 : 1,
            display: 'flex', alignItems: 'center', gap: 8,
          }}>
            {pinging ? '⏳ Testando...' : '📡 Testar Conectividade (Ping)'}
          </button>
          {(!onu.assigned_ip && !onu.pppoe_username) && (
            <div style={{ fontSize: 12, color: '#9ca3af', marginTop: 6 }}>
              Sem IP cadastrado ou usuário PPPoE no contrato
            </div>
          )}
          {pingResult && (
            <div style={{
              marginTop: 12, padding: '12px 16px', borderRadius: 10,
              background: pingResult.error ? '#fee2e2' : pingResult.is_reachable ? '#d1fae5' : '#fee2e2',
              border: `1px solid ${pingResult.error ? '#fca5a5' : pingResult.is_reachable ? '#6ee7b7' : '#fca5a5'}`,
              fontSize: 13, color: '#111827',
            }}>
              {pingResult.error ? `❌ ${pingResult.error}` : pingResult.is_reachable
                ? `✅ Responde em ${formatLatency(pingResult.latencia_ms)} (IP: ${pingResult.ip_testado || '—'})`
                : `❌ Host não responde (IP: ${pingResult.ip_testado || '—'})`}
            </div>
          )}
        </div>

        {/* Histórico */}
        <div>
          <h3 style={{ fontSize: 15, fontWeight: 700, color: '#374151', marginBottom: 12 }}>
            📈 Histórico — últimas 24h
          </h3>
          {loading ? (
            <div style={{ textAlign: 'center', padding: 20, color: '#9ca3af' }}>Carregando histórico...</div>
          ) : history.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 20, color: '#9ca3af' }}>Sem dados de histórico ainda</div>
          ) : (
            <div>
              <MiniChart snapshots={history} />
              <div style={{ marginTop: 12, maxHeight: 180, overflow: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                  <thead>
                    <tr style={{ background: '#f9fafb' }}>
                      {['Horário', 'Status', 'Latência'].map(h => (
                        <th key={h} style={{ padding: '8px 10px', textAlign: 'left', color: '#6b7280', fontWeight: 600, borderBottom: '1px solid #e5e7eb' }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {[...history].reverse().slice(0, 30).map(s => (
                      <tr key={s.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                        <td style={{ padding: '7px 10px', color: '#374151' }}>{formatDate(s.timestamp)}</td>
                        <td style={{ padding: '7px 10px' }}><StatusBadge status={s.status} /></td>
                        <td style={{ padding: '7px 10px', color: '#374151' }}>{formatLatency(s.latencia_ms)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

/** Modal de criação/edição de OLT */
const OLTModal: React.FC<{
  olt?: OLT | null; onClose: () => void; onSave: (data: any) => void; saving: boolean;
}> = ({ olt, onClose, onSave, saving }) => {
  const [form, setForm] = useState({
    nome: olt?.nome || '',
    ip: olt?.ip || '',
    porta_snmp: olt?.porta_snmp || 161,
    community_read: olt?.community_read || '',
    fabricante: olt?.fabricante || '',
    modelo: olt?.modelo || '',
    localizacao: olt?.localizacao || '',
    descricao: olt?.descricao || '',
    is_active: olt?.is_active ?? true,
  });

  const field = (label: string, key: string, type = 'text', placeholder = '') => (
    <div>
      <label style={{ fontSize: 12, fontWeight: 600, color: '#374151', display: 'block', marginBottom: 4 }}>{label}</label>
      <input type={type} value={String(form[key as keyof typeof form])}
        placeholder={placeholder}
        onChange={e => setForm(f => ({ ...f, [key]: type === 'number' ? Number(e.target.value) : e.target.value }))}
        style={{ width: '100%', padding: '9px 12px', borderRadius: 8, border: '1px solid #d1d5db', fontSize: 14, boxSizing: 'border-box' }}
      />
    </div>
  );

  return (
    <div style={{ position: 'fixed', inset: 0, zIndex: 1000, background: 'rgba(0,0,0,0.55)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20 }} onClick={onClose}>
      <div style={{ background: '#fff', borderRadius: 20, padding: 32, maxWidth: 580, width: '100%', boxShadow: '0 24px 64px rgba(0,0,0,0.2)', maxHeight: '90vh', overflowY: 'auto' }} onClick={e => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
          <h2 style={{ fontSize: 18, fontWeight: 800, margin: 0 }}>{olt ? 'Editar OLT' : 'Nova OLT'}</h2>
          <button onClick={onClose} style={{ background: '#f3f4f6', border: 'none', borderRadius: 8, width: 36, height: 36, cursor: 'pointer', fontSize: 18, color: '#6b7280' }}>✕</button>
        </div>

        {/* Campos base */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {field('Nome *', 'nome', 'text', 'Ex: OLT-Centro')}
          {field('Endereço IP *', 'ip', 'text', 'Ex: 192.168.1.1')}
          {field('Porta SNMP', 'porta_snmp', 'number', '161')}
          {field('Community SNMP (leitura)', 'community_read', 'text', 'public')}
          {field('Fabricante', 'fabricante', 'text', 'ZTE, Huawei, Fiberhome...')}
          {field('Modelo', 'modelo', 'text', 'C300, MA5800...')}
          {field('Localização', 'localizacao', 'text', 'Ex: Sala de equipamentos - Matriz')}
        </div>

        <div style={{ display: 'flex', gap: 12, marginTop: 24, justifyContent: 'flex-end' }}>
          <button onClick={onClose} style={{ padding: '10px 20px', borderRadius: 10, border: '1px solid #d1d5db', background: '#fff', cursor: 'pointer', fontWeight: 600 }}>Cancelar</button>
          <button onClick={() => {
            onSave(form);
          }} disabled={saving || !form.nome || !form.ip} style={{
            padding: '10px 20px', borderRadius: 10, border: 'none',
            background: '#4f46e5', color: '#fff', cursor: saving ? 'not-allowed' : 'pointer',
            fontWeight: 700, opacity: saving ? 0.7 : 1,
          }}>
            {saving ? 'Salvando...' : 'Salvar'}
          </button>
        </div>
      </div>
    </div>
  );
};

/** Modal de criação/edição de CTO */
const CTOModal: React.FC<{
  cto?: CTO | null; olts: OLT[]; ctos: CTO[]; onClose: () => void; onSave: (data: any) => void; saving: boolean;
}> = ({ cto, olts, ctos, onClose, onSave, saving }) => {
  const { activeCompany } = useCompany();
  const [form, setForm] = useState({
    nome: cto?.nome || '',
    olt_id: cto?.olt_id || '',
    porta_pon: cto?.porta_pon || '',
    splitter_ratio: cto?.splitter_ratio || '',
    capacidade: cto?.capacidade || '',
    coordenadas_gps: cto?.coordenadas_gps || '',
    endereco: cto?.endereco || '',
    descricao: cto?.descricao || '',
    is_active: cto?.is_active ?? true,
  });

  const [mapCenter, setMapCenter] = useState<[number, number]>([-23.5489, -46.6388]);
  const [mapZoom, setMapZoom] = useState<number>(14);
  const [geocoding, setGeocoding] = useState<boolean>(false);
  const [geocodeError, setGeocodeError] = useState<string | null>(null);



  const geocodeAddress = async (addressStr: string) => {
    if (!addressStr || addressStr.trim() === '') return;
    setGeocoding(true);
    setGeocodeError(null);

    // Normalize and clean address
    const cleanStr = addressStr.replace(/[\-\/]/g, ','); // replace dashes and slashes with commas
    const parts = cleanStr.split(',').map(p => p.trim()).filter(Boolean);

    const queries: string[] = [addressStr];

    if (parts.length >= 3) {
      // Try Street + City/State
      queries.push(`${parts[0]}, ${parts[parts.length - 1]}`);

      // Try Street (no numbers) + City/State
      const streetNoNum = parts[0].replace(/\d+/g, '').trim();
      if (streetNoNum && streetNoNum !== parts[0]) {
        queries.push(`${streetNoNum}, ${parts[parts.length - 1]}`);
      }
    }

    // Try just City/State
    if (parts.length >= 2) {
      queries.push(parts[parts.length - 1]);
    }

    let found = false;
    for (const query of queries) {
      try {
        const response = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&limit=1`, {
          headers: { 'Accept-Language': 'pt-BR,pt;q=0.9' }
        });
        if (response.ok) {
          const data = await response.json();
          if (data && data.length > 0) {
            const { lat, lon } = data[0];
            const latF = parseFloat(lat);
            const lonF = parseFloat(lon);
            const coordsStr = `${latF.toFixed(6)},${lonF.toFixed(6)}`;
            setForm(prev => ({ ...prev, coordenadas_gps: coordsStr }));
            setMapCenter([latF, lonF]);
            setMapZoom(16);
            found = true;
            break;
          }
        }
      } catch (err) {
        console.error(`Erro ao geocodificar query "${query}":`, err);
      }
    }

    setGeocoding(false);
    if (!found) {
      setGeocodeError('Endereço não localizado. Tente simplificar a busca.');
    }
  };

  useEffect(() => {
    const initMap = async () => {
      const initialCoords = parseCoords(form.coordenadas_gps);
      if (initialCoords) {
        setMapCenter(initialCoords);
        setMapZoom(16);
      } else if (form.endereco) {
        await geocodeAddress(form.endereco);
      } else if (activeCompany && activeCompany.endereco) {
        const providerAddr = `${activeCompany.endereco}, ${activeCompany.numero || ''}, ${activeCompany.municipio || ''} - ${activeCompany.uf || ''}, Brasil`;
        await geocodeAddress(providerAddr);
      } else {
        const firstWithCoords = ctos.find(c => parseCoords(c.coordenadas_gps) !== null);
        if (firstWithCoords) {
          const pc = parseCoords(firstWithCoords.coordenadas_gps);
          if (pc) {
            setMapCenter(pc);
            setMapZoom(14);
          }
        }
      }
    };
    initMap();
  }, []);

  const ctoIcon = L.divIcon({
    html: `<div style="display: flex; justify-content: center; align-items: center; width: 32px; height: 32px; background-color: #8b5cf6; border-radius: 50% 50% 50% 0; transform: rotate(-45deg); border: 2.5px solid white; box-shadow: 0 3px 6px rgba(0,0,0,0.35);">
            <div style="width: 10px; height: 10px; background-color: white; border-radius: 50%; transform: rotate(45deg);"></div>
          </div>`,
    className: 'custom-cto-pin',
    iconSize: [32, 32],
    iconAnchor: [16, 32]
  });



  const handleMapClick = async (latlng: L.LatLng) => {
    const coordsStr = `${latlng.lat.toFixed(6)},${latlng.lng.toFixed(6)}`;
    setForm(prev => ({ ...prev, coordenadas_gps: coordsStr }));
    setMapCenter([latlng.lat, latlng.lng]);
    
    try {
      const response = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${latlng.lat}&lon=${latlng.lng}&zoom=18`, {
        headers: { 'Accept-Language': 'pt-BR,pt;q=0.9' }
      });
      if (response.ok) {
        const data = await response.json();
        if (data && data.display_name) {
          setForm(prev => ({ ...prev, endereco: data.display_name }));
        }
      }
    } catch (err) {
      console.error("Erro ao obter endereço por coordenadas:", err);
    }
  };

  const initialCoords = parseCoords(form.coordenadas_gps);

  return (
    <div style={{ position: 'fixed', inset: 0, zIndex: 1000, background: 'rgba(0,0,0,0.55)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20 }} onClick={onClose}>
      <div style={{ 
        background: '#fff', 
        borderRadius: 20, 
        padding: 32, 
        maxWidth: 960, 
        width: '100%', 
        boxShadow: '0 24px 64px rgba(0,0,0,0.2)', 
        maxHeight: '90vh', 
        overflow: 'auto',
        boxSizing: 'border-box'
      }} onClick={e => e.stopPropagation()}>
        
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
          <h2 style={{ fontSize: 18, fontWeight: 800, margin: 0 }}>{cto ? 'Editar CTO' : 'Nova CTO'}</h2>
          <button onClick={onClose} style={{ background: '#f3f4f6', border: 'none', borderRadius: 8, width: 36, height: 36, cursor: 'pointer', fontSize: 18, color: '#6b7280' }}>✕</button>
        </div>

        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', 
          gap: 24 
        }}>
          {/* Col 1: Inputs */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {[
              { label: 'Nome *', key: 'nome', placeholder: 'Ex: CTO-001-Centro' },
              { label: 'Porta PON', key: 'porta_pon', placeholder: 'Ex: 0/1/1' },
              { label: 'Splitter', key: 'splitter_ratio', placeholder: 'Ex: 1:8, 1:16, 1:32' },
              { label: 'Capacidade (ONUs)', key: 'capacidade', type: 'number', placeholder: '8' },
              { label: 'Coordenadas GPS', key: 'coordenadas_gps', placeholder: '-23.1234,-46.5678' },
              { label: 'Endereço', key: 'endereco', placeholder: 'Rua das Flores, 123' },
              { label: 'Descrição', key: 'descricao', placeholder: 'Ex: Poste em frente ao número 10' }
            ].map(f => {
              if (f.key === 'endereco') {
                return (
                  <div key={f.key}>
                    <label style={{ fontSize: 12, fontWeight: 600, color: '#374151', display: 'block', marginBottom: 4 }}>{f.label}</label>
                    <div style={{ display: 'flex', gap: 8 }}>
                      <input type="text" value={String(form.endereco || '')}
                        placeholder={f.placeholder}
                        onChange={e => setForm(prev => ({ ...prev, endereco: e.target.value }))}
                        onBlur={() => geocodeAddress(form.endereco)}
                        style={{ flex: 1, padding: '9px 12px', borderRadius: 8, border: '1px solid #d1d5db', fontSize: 14, boxSizing: 'border-box' }}
                      />
                      <button type="button" onClick={() => geocodeAddress(form.endereco)} disabled={geocoding} style={{
                        padding: '9px 16px', borderRadius: 8, border: '1px solid #4f46e5',
                        background: '#fff', color: '#4f46e5', cursor: geocoding ? 'not-allowed' : 'pointer', fontWeight: 600, fontSize: 13,
                        transition: 'all 0.2s', whiteSpace: 'nowrap', opacity: geocoding ? 0.6 : 1
                      }}
                      onMouseEnter={e => { if (!geocoding) e.currentTarget.style.background = '#eef2ff'; }}
                      onMouseLeave={e => { if (!geocoding) e.currentTarget.style.background = '#fff'; }}
                      >
                        {geocoding ? '⏳ Buscando...' : '🔍 Buscar'}
                      </button>
                    </div>
                    {geocodeError && (
                      <span style={{ fontSize: 11, color: '#ef4444', display: 'block', marginTop: 4 }}>
                        ⚠️ {geocodeError}
                      </span>
                    )}
                  </div>
                );
              }
              return (
                <div key={f.key}>
                  <label style={{ fontSize: 12, fontWeight: 600, color: '#374151', display: 'block', marginBottom: 4 }}>{f.label}</label>
                  <input type={f.type || 'text'} value={String(form[f.key as keyof typeof form] || '')}
                    placeholder={f.placeholder}
                    onChange={e => setForm(prev => ({ ...prev, [f.key]: f.type === 'number' ? Number(e.target.value) || '' : e.target.value }))}
                    onBlur={() => {
                      if (f.key === 'coordenadas_gps') {
                        const parsed = parseCoords(form.coordenadas_gps);
                        if (parsed) {
                          setMapCenter(parsed);
                          setMapZoom(16);
                        }
                      }
                    }}
                    style={{ width: '100%', padding: '9px 12px', borderRadius: 8, border: '1px solid #d1d5db', fontSize: 14, boxSizing: 'border-box' }}
                  />
                </div>
              );
            })}
            <div>
              <label style={{ fontSize: 12, fontWeight: 600, color: '#374151', display: 'block', marginBottom: 4 }}>OLT Vinculada</label>
              <select value={form.olt_id} onChange={e => setForm(f => ({ ...f, olt_id: e.target.value }))}
                style={{ width: '100%', padding: '9px 12px', borderRadius: 8, border: '1px solid #d1d5db', fontSize: 14 }}>
                <option value="">— Nenhuma —</option>
                {olts.map(o => <option key={o.id} value={o.id}>{o.nome} ({o.ip})</option>)}
              </select>
            </div>
          </div>

          {/* Col 2: Map Selection */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div>
              <label style={{ fontSize: 12, fontWeight: 600, color: '#374151', display: 'block', marginBottom: 2 }}>
                Selecione a Localização no Mapa
              </label>
              <span style={{ fontSize: 11, color: '#6b7280', display: 'block', marginBottom: 8 }}>
                Clique no mapa para marcar o ponto exato da CTO. Coordenadas e endereço serão preenchidos automaticamente.
              </span>
            </div>

            <div style={{ 
              height: 420, 
              width: '100%', 
              borderRadius: 12, 
              overflow: 'hidden', 
              border: '1px solid #d1d5db',
              position: 'relative'
            }}>
              <MapContainer
                center={mapCenter}
                zoom={mapZoom}
                style={{ height: '100%', width: '100%' }}
              >
                <TileLayer
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />
                
                <MapClickEvents onClick={handleMapClick} />
                <ChangeMapCenter center={mapCenter} zoom={mapZoom} />

                {initialCoords && (
                  <Marker position={initialCoords} icon={ctoIcon} />
                )}
              </MapContainer>
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', gap: 12, marginTop: 28, justifyContent: 'flex-end', borderTop: '1px solid #f3f4f6', paddingTop: 20 }}>
          <button onClick={onClose} style={{ padding: '10px 20px', borderRadius: 10, border: '1px solid #d1d5db', background: '#fff', cursor: 'pointer', fontWeight: 600 }}>Cancelar</button>
          <button onClick={() => onSave({ ...form, olt_id: form.olt_id ? Number(form.olt_id) : null, capacidade: Number(form.capacidade) || null })}
            disabled={saving || !form.nome} style={{
              padding: '10px 20px', borderRadius: 10, border: 'none',
              background: '#4f46e5', color: '#fff', cursor: saving ? 'not-allowed' : 'pointer',
              fontWeight: 700, opacity: saving ? 0.7 : 1,
            }}>
            {saving ? 'Salvando...' : 'Salvar'}
          </button>
        </div>
      </div>
    </div>
  );
};

// ============================================================
// PÁGINA PRINCIPAL
// ============================================================
const FTTHMonitor: React.FC = () => {
  const { activeCompany } = useCompany();
  useAuth(); // Manter contexto de autenticação ativo
  const empresaId = activeCompany?.id;
  const token = authService.getStoredToken();

  const [activeTab, setActiveTab] = useState<'dashboard' | 'onts' | 'infra' | 'historico' | 'mapa'>('dashboard');
  const [infraTab, setInfraTab] = useState<'olts' | 'ctos'>('olts');

  // Dashboard
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [dashLoading, setDashLoading] = useState(false);

  // ONUs
  const [onus, setOnus] = useState<ONUStatus[]>([]);
  const [onusTotal, setOnusTotal] = useState(0);
  const [onusLoading, setOnusLoading] = useState(false);
  const [onusPage, setOnusPage] = useState(1);
  const [onusLimit, setOnusLimit] = useState(10);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [oltFilter, setOltFilter] = useState('');
  const [selectedONU, setSelectedONU] = useState<ONUStatus | null>(null);
  const [pollingAll, setPollingAll] = useState(false);

  // OLTs
  const [olts, setOlts] = useState<OLT[]>([]);
  const [oltModal, setOltModal] = useState<{ open: boolean; olt?: OLT | null }>({ open: false });
  const [oltSaving, setOltSaving] = useState(false);

  // CTOs
  const [ctos, setCtos] = useState<CTO[]>([]);
  const [ctoModal, setCtoModal] = useState<{ open: boolean; cto?: CTO | null }>({ open: false });
  const [ctoSaving, setCtoSaving] = useState(false);

  // Alertas
  const [alertas, setAlertas] = useState<ONUStatus[]>([]);

  const headers = token ? getAuthHeaders(token, empresaId) : {};

  // ---- Loaders ----
  const loadDashboard = useCallback(async () => {
    if (!empresaId || !token) return;
    setDashLoading(true);
    try {
      const r = await axios.get(`${API_BASE}/ftth/dashboard`, { headers });
      setDashboard(r.data);
    } catch { } finally { setDashLoading(false); }
  }, [empresaId, token]);

  const loadONUs = useCallback(async () => {
    if (!empresaId || !token) return;
    setOnusLoading(true);
    try {
      const params: any = {
        limit: onusLimit,
        skip: (onusPage - 1) * onusLimit
      };
      if (search) params.search = search;
      if (statusFilter) params.status = statusFilter;
      if (oltFilter) params.olt_nome = oltFilter;
      const r = await axios.get(`${API_BASE}/ftth/onts`, { headers, params });
      setOnus(r.data.data);
      setOnusTotal(r.data.total);
    } catch { } finally { setOnusLoading(false); }
  }, [empresaId, token, onusPage, onusLimit, search, statusFilter, oltFilter]);

  // Reseta para a primeira página quando os filtros mudam
  useEffect(() => {
    setOnusPage(1);
  }, [search, statusFilter, oltFilter]);

  const loadOLTs = useCallback(async () => {
    if (!empresaId || !token) return;
    try {
      const r = await axios.get(`${API_BASE}/ftth/olts`, { headers });
      setOlts(r.data);
    } catch { }
  }, [empresaId, token]);

  const loadCTOs = useCallback(async () => {
    if (!empresaId || !token) return;
    try {
      const r = await axios.get(`${API_BASE}/ftth/ctos`, { headers });
      setCtos(r.data);
    } catch { }
  }, [empresaId, token]);

  const loadAlertas = useCallback(async () => {
    if (!empresaId || !token) return;
    try {
      const r = await axios.get(`${API_BASE}/ftth/alertas`, { headers });
      setAlertas(r.data.data);
    } catch { }
  }, [empresaId, token]);

  // Carregamento inicial
  useEffect(() => { loadDashboard(); loadAlertas(); }, [loadDashboard, loadAlertas]);
  useEffect(() => {
    if (activeTab === 'onts') {
      loadONUs();
    } else if (activeTab === 'mapa') {
      loadONUs();
      loadCTOs();
    }
  }, [activeTab, loadONUs, loadCTOs]);
  useEffect(() => { if (activeTab === 'infra') { loadOLTs(); loadCTOs(); } }, [activeTab, loadOLTs, loadCTOs]);

  // Auto-refresh a cada 2 minutos
  useEffect(() => {
    const id = setInterval(() => {
      loadDashboard();
      loadAlertas();
      if (activeTab === 'onts' || activeTab === 'mapa') loadONUs();
    }, 120_000);
    return () => clearInterval(id);
  }, [activeTab, loadDashboard, loadAlertas, loadONUs]);

  // ---- Ações OLT ----
  const handleSaveOLT = async (data: any) => {
    setOltSaving(true);
    try {
      if (oltModal.olt) {
        await axios.put(`${API_BASE}/ftth/olts/${oltModal.olt.id}`, data, { headers });
      } else {
        await axios.post(`${API_BASE}/ftth/olts`, data, { headers });
      }
      setOltModal({ open: false });
      loadOLTs();
    } catch { } finally { setOltSaving(false); }
  };

  const handleDeleteOLT = async (id: number) => {
    if (!window.confirm('Remover esta OLT?')) return;
    try {
      await axios.delete(`${API_BASE}/ftth/olts/${id}`, { headers });
      loadOLTs();
    } catch { }
  };

  // ---- Ações CTO ----
  const handleSaveCTO = async (data: any) => {
    setCtoSaving(true);
    try {
      if (ctoModal.cto) {
        await axios.put(`${API_BASE}/ftth/ctos/${ctoModal.cto.id}`, data, { headers });
      } else {
        await axios.post(`${API_BASE}/ftth/ctos`, data, { headers });
      }
      setCtoModal({ open: false });
      loadCTOs();
    } catch { } finally { setCtoSaving(false); }
  };

  const handleDeleteCTO = async (id: number) => {
    if (!window.confirm('Remover esta CTO?')) return;
    try {
      await axios.delete(`${API_BASE}/ftth/ctos/${id}`, { headers });
      loadCTOs();
    } catch { }
  };

  // ---- Poll All ----
  const handlePollAll = async () => {
    setPollingAll(true);
    try {
      await axios.post(`${API_BASE}/ftth/poll-all`, {}, { headers });
      setTimeout(() => { loadDashboard(); loadONUs(); loadAlertas(); }, 3000);
    } catch { } finally { setTimeout(() => setPollingAll(false), 3000); }
  };

  // ============================================================
  // RENDER TABS
  // ============================================================

  const renderDashboard = () => (
    <div>
      {/* Alertas de destaque */}
      {alertas.length > 0 && (
        <div style={{
          background: 'linear-gradient(135deg, #fee2e2, #fef3c7)',
          border: '1px solid #fca5a5', borderRadius: 16, padding: '16px 20px', marginBottom: 24,
          display: 'flex', alignItems: 'flex-start', gap: 14,
        }}>
          <span style={{ fontSize: 24 }}>⚠️</span>
          <div>
            <div style={{ fontWeight: 800, color: '#991b1b', fontSize: 15 }}>
              {alertas.length} ONU{alertas.length > 1 ? 's' : ''} com problema
            </div>
            <div style={{ color: '#7f1d1d', fontSize: 13, marginTop: 4 }}>
              {alertas.slice(0, 3).map(a => a.cliente_nome).join(', ')}
              {alertas.length > 3 && ` e mais ${alertas.length - 3}...`}
            </div>
          </div>
          <button onClick={() => { setActiveTab('onts'); setStatusFilter('OFFLINE'); }}
            style={{ marginLeft: 'auto', background: '#ef4444', color: '#fff', border: 'none', borderRadius: 8, padding: '8px 16px', cursor: 'pointer', fontWeight: 700, fontSize: 13 }}>
            Ver Alertas
          </button>
        </div>
      )}

      {/* KPI Cards */}
      {dashLoading ? (
        <div style={{ textAlign: 'center', padding: 60, color: '#9ca3af' }}>Carregando dados...</div>
      ) : dashboard ? (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16, marginBottom: 28 }}>
            <KPICard icon="📡" label="Total ONUs FTTH" value={dashboard.total_onus} color="#4f46e5" bg="#eef2ff" />
            <KPICard icon="🟢" label="Online" value={dashboard.onus_online} color="#10b981" bg="#d1fae5"
              sub={`${dashboard.disponibilidade_percentual.toFixed(1)}% disponibilidade`} />
            <KPICard icon="🔴" label="Offline" value={dashboard.onus_offline} color="#ef4444" bg="#fee2e2" />
            <KPICard icon="🟡" label="Degradado" value={dashboard.onus_degradado} color="#f59e0b" bg="#fef3c7" />
            <KPICard icon="⚪" label="Desconhecido" value={dashboard.onus_desconhecido} color="#6b7280" bg="#f3f4f6" />
            <KPICard icon="🏗️" label="OLTs" value={dashboard.total_olts} color="#3b82f6" bg="#dbeafe" />
            <KPICard icon="📦" label="CTOs" value={dashboard.total_ctos} color="#8b5cf6" bg="#ede9fe" />
          </div>

          {/* Disponibilidade Barra */}
          <div style={{ background: '#fff', borderRadius: 16, padding: 24, boxShadow: '0 2px 12px rgba(0,0,0,0.07)', marginBottom: 24 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <div style={{ fontWeight: 700, color: '#374151' }}>Disponibilidade Geral</div>
              <div style={{ fontWeight: 800, fontSize: 22, color: dashboard.disponibilidade_percentual >= 95 ? '#10b981' : dashboard.disponibilidade_percentual >= 80 ? '#f59e0b' : '#ef4444' }}>
                {dashboard.disponibilidade_percentual.toFixed(1)}%
              </div>
            </div>
            <div style={{ background: '#f3f4f6', borderRadius: 99, height: 12, overflow: 'hidden' }}>
              <div style={{
                height: '100%', borderRadius: 99, transition: 'width 1s ease',
                width: `${dashboard.disponibilidade_percentual}%`,
                background: dashboard.disponibilidade_percentual >= 95
                  ? 'linear-gradient(90deg, #10b981, #34d399)'
                  : dashboard.disponibilidade_percentual >= 80
                    ? 'linear-gradient(90deg, #f59e0b, #fbbf24)'
                    : 'linear-gradient(90deg, #ef4444, #f87171)',
              }} />
            </div>
            {dashboard.ultima_atualizacao && (
              <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 8 }}>
                Última atualização: {formatDate(dashboard.ultima_atualizacao)}
              </div>
            )}
          </div>

          {/* Lista de Alertas */}
          {alertas.length > 0 && (
            <div style={{ background: '#fff', borderRadius: 16, padding: 24, boxShadow: '0 2px 12px rgba(0,0,0,0.07)' }}>
              <h3 style={{ fontWeight: 800, color: '#374151', marginBottom: 16, fontSize: 15 }}>🚨 Alertas Ativos</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {alertas.slice(0, 10).map(a => (
                  <div key={a.contrato_id} style={{
                    display: 'flex', alignItems: 'center', gap: 12,
                    padding: '10px 14px', borderRadius: 10, background: '#fafafa', border: '1px solid #e5e7eb',
                  }}>
                    <StatusBadge status={a.status} />
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 700, fontSize: 14, color: '#111827' }}>{a.cliente_nome}</div>
                      <div style={{ fontSize: 12, color: '#6b7280' }}>{a.olt_nome || 'OLT n/d'} — {a.cto_nome || 'CTO n/d'} — {a.assigned_ip || 'sem IP'}</div>
                    </div>
                    <div style={{ fontSize: 11, color: '#9ca3af' }}>{formatDate(a.ultima_verificacao)}</div>
                    <button onClick={() => setSelectedONU(a)} style={{
                      background: '#4f46e5', color: '#fff', border: 'none', borderRadius: 8,
                      padding: '6px 12px', cursor: 'pointer', fontSize: 12, fontWeight: 600,
                    }}>Detalhes</button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      ) : (
        <div style={{ textAlign: 'center', padding: 60, color: '#9ca3af' }}>
          <div style={{ fontSize: 48, marginBottom: 12 }}>📡</div>
          <div style={{ fontSize: 16, fontWeight: 600 }}>Nenhum dado disponível</div>
          <div style={{ fontSize: 13, marginTop: 4 }}>Verifique se há contratos FTTH cadastrados com ONU Serial ou tipo de conexão FIBRA.</div>
        </div>
      )}
    </div>
  );

  const totalPages = Math.ceil(onusTotal / onusLimit);
  
  const renderPagination = () => {
    if (totalPages <= 1) return null;
    return (
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 20px', borderTop: '1px solid #e5e7eb', background: '#fff', flexWrap: 'wrap', gap: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
          <div style={{ fontSize: 13, color: '#6b7280', fontWeight: 600 }}>
            Exibindo {Math.min((onusPage - 1) * onusLimit + 1, onusTotal)} a {Math.min(onusPage * onusLimit, onusTotal)} de {onusTotal} ONUs
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <label style={{ fontSize: 12, color: '#6b7280', fontWeight: 600 }}>Itens por página:</label>
            <select 
              value={onusLimit} 
              onChange={e => { setOnusLimit(Number(e.target.value)); setOnusPage(1); }}
              style={{ padding: '4px 8px', borderRadius: 6, border: '1px solid #d1d5db', fontSize: 13, outline: 'none' }}
            >
              {[10, 25, 50, 100].map(v => <option key={v} value={v}>{v}</option>)}
            </select>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          <button 
            disabled={onusPage === 1}
            onClick={() => setOnusPage(p => Math.max(p - 1, 1))}
            style={{
              padding: '6px 12px', borderRadius: 8, border: '1px solid #d1d5db',
              background: onusPage === 1 ? '#f3f4f6' : '#fff',
              color: onusPage === 1 ? '#9ca3af' : '#374151',
              cursor: onusPage === 1 ? 'not-allowed' : 'pointer',
              fontWeight: 700, fontSize: 13, transition: 'all 0.2s'
            }}
          >
            Anterior
          </button>
          
          {Array.from({ length: totalPages }).map((_, i) => {
            const p = i + 1;
            if (totalPages > 6 && Math.abs(onusPage - p) > 2 && p !== 1 && p !== totalPages) {
              if (p === 2 || p === totalPages - 1) {
                return <span key={`ellipsis-${p}`} style={{ padding: '6px', color: '#9ca3af' }}>...</span>;
              }
              return null;
            }
            return (
              <button
                key={`page-${p}`}
                onClick={() => setOnusPage(p)}
                style={{
                  minWidth: 32, padding: '6px 8px', borderRadius: 8,
                  background: onusPage === p ? '#4f46e5' : '#fff',
                  color: onusPage === p ? '#fff' : '#374151',
                  border: onusPage === p ? 'none' : '1px solid #d1d5db',
                  cursor: 'pointer', fontWeight: 700, fontSize: 13, transition: 'all 0.2s'
                }}
              >
                {p}
              </button>
            );
          })}

          <button 
            disabled={onusPage === totalPages}
            onClick={() => setOnusPage(p => Math.min(p + 1, totalPages))}
            style={{
              padding: '6px 12px', borderRadius: 8, border: '1px solid #d1d5db',
              background: onusPage === totalPages ? '#f3f4f6' : '#fff',
              color: onusPage === totalPages ? '#9ca3af' : '#374151',
              cursor: onusPage === totalPages ? 'not-allowed' : 'pointer',
              fontWeight: 700, fontSize: 13, transition: 'all 0.2s'
            }}
          >
            Próxima
          </button>
        </div>
      </div>
    );
  };

  const renderONTs = () => (
    <div>
      {/* Filtros */}
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 20 }}>
        <input value={search} onChange={e => setSearch(e.target.value)}
          placeholder="🔍 Buscar por cliente, serial ou contrato..."
          style={{ flex: 1, minWidth: 200, padding: '10px 14px', borderRadius: 10, border: '1px solid #d1d5db', fontSize: 14 }}
        />
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
          style={{ padding: '10px 14px', borderRadius: 10, border: '1px solid #d1d5db', fontSize: 14 }}>
          <option value="">Todos os status</option>
          <option value="ONLINE">🟢 Online</option>
          <option value="OFFLINE">🔴 Offline</option>
          <option value="DEGRADADO">🟡 Degradado</option>
          <option value="DESCONHECIDO">⚪ Desconhecido</option>
        </select>
        <input value={oltFilter} onChange={e => setOltFilter(e.target.value)}
          placeholder="Filtrar por OLT..."
          style={{ width: 180, padding: '10px 14px', borderRadius: 10, border: '1px solid #d1d5db', fontSize: 14 }}
        />
        <button onClick={loadONUs} style={{
          background: '#4f46e5', color: '#fff', border: 'none', borderRadius: 10,
          padding: '10px 18px', cursor: 'pointer', fontWeight: 700, fontSize: 14,
        }}>Filtrar</button>
        <button onClick={handlePollAll} disabled={pollingAll} style={{
          background: pollingAll ? '#9ca3af' : '#059669', color: '#fff', border: 'none', borderRadius: 10,
          padding: '10px 18px', cursor: pollingAll ? 'not-allowed' : 'pointer', fontWeight: 700, fontSize: 14,
        }}>
          {pollingAll ? '⏳ Verificando...' : '🔄 Verificar Todas'}
        </button>
      </div>

      {/* Tabela */}
      {onusLoading ? (
        <div style={{ textAlign: 'center', padding: 60, color: '#9ca3af' }}>Carregando ONUs...</div>
      ) : (
        <div style={{ background: '#fff', borderRadius: 16, boxShadow: '0 2px 12px rgba(0,0,0,0.07)', overflow: 'hidden' }}>
          <div style={{ padding: '14px 20px', borderBottom: '1px solid #e5e7eb', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ fontWeight: 700, color: '#374151', fontSize: 15 }}>
              ONUs FTTH — {onusTotal} total ({onus.length} nesta página)
            </div>
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ background: '#f9fafb' }}>
                  {['Status', 'Cliente', 'ONU Serial', 'OLT / PON', 'CTO', 'IP', 'Latência', 'Última Verificação', 'Ações'].map(h => (
                    <th key={h} style={{ padding: '12px 14px', textAlign: 'left', color: '#6b7280', fontWeight: 700, fontSize: 12, borderBottom: '1px solid #e5e7eb', whiteSpace: 'nowrap' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {onus.length === 0 ? (
                  <tr><td colSpan={9} style={{ padding: 40, textAlign: 'center', color: '#9ca3af' }}>
                    Nenhuma ONU encontrada com os filtros aplicados
                  </td></tr>
                ) : onus.map(onu => (
                  <tr key={onu.contrato_id} style={{ borderBottom: '1px solid #f3f4f6', transition: 'background 0.15s' }}
                    onMouseEnter={e => (e.currentTarget.style.background = '#f9fafb')}
                    onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}>
                    <td style={{ padding: '12px 14px' }}><StatusBadge status={onu.status} /></td>
                    <td style={{ padding: '12px 14px' }}>
                      <div style={{ fontWeight: 700, color: '#111827' }}>{onu.cliente_nome}</div>
                      {onu.numero_contrato && <div style={{ fontSize: 11, color: '#9ca3af' }}>#{onu.numero_contrato}</div>}
                    </td>
                    <td style={{ padding: '12px 14px', fontFamily: 'monospace', color: '#374151' }}>{onu.onu_serial || '—'}</td>
                    <td style={{ padding: '12px 14px', color: '#374151' }}>
                      {onu.olt_nome || '—'}
                      {onu.olt_pon && <div style={{ fontSize: 11, color: '#9ca3af' }}>{onu.olt_pon}</div>}
                    </td>
                    <td style={{ padding: '12px 14px', color: '#374151' }}>{onu.cto_nome || '—'}</td>
                    <td style={{ padding: '12px 14px', fontFamily: 'monospace', fontSize: 12, color: '#374151' }}>{onu.assigned_ip || '—'}</td>
                    <td style={{ padding: '12px 14px', color: onu.latencia_ms && onu.latencia_ms > 100 ? '#f59e0b' : '#374151' }}>
                      {formatLatency(onu.latencia_ms)}
                    </td>
                    <td style={{ padding: '12px 14px', fontSize: 11, color: '#9ca3af', whiteSpace: 'nowrap' }}>
                      {formatDate(onu.ultima_verificacao)}
                    </td>
                    <td style={{ padding: '12px 14px' }}>
                      <button onClick={() => setSelectedONU(onu)} style={{
                        background: '#4f46e5', color: '#fff', border: 'none', borderRadius: 7,
                        padding: '6px 12px', cursor: 'pointer', fontWeight: 700, fontSize: 12,
                      }}>Detalhes</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {renderPagination()}
        </div>
      )}
    </div>
  );

  const renderInfra = () => (
    <div>
      {/* Sub-tabs OLTs / CTOs */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 24, background: '#f3f4f6', borderRadius: 12, padding: 4, width: 'fit-content' }}>
        {[
          { key: 'olts', label: '📡 OLTs' },
          { key: 'ctos', label: '📦 CTOs' },
        ].map(({ key, label }) => (
          <button key={key} onClick={() => setInfraTab(key as any)} style={{
            padding: '8px 20px', borderRadius: 10, border: 'none', cursor: 'pointer',
            fontWeight: 700, fontSize: 14,
            background: infraTab === key ? '#4f46e5' : 'transparent',
            color: infraTab === key ? '#fff' : '#6b7280',
            transition: 'all 0.2s',
          }}>{label}</button>
        ))}
      </div>

      {infraTab === 'olts' && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <div style={{ fontWeight: 700, color: '#374151', fontSize: 15 }}>OLTs Cadastradas — {olts.length}</div>
            <button onClick={() => setOltModal({ open: true, olt: null })} style={{
              background: '#4f46e5', color: '#fff', border: 'none', borderRadius: 10,
              padding: '10px 18px', cursor: 'pointer', fontWeight: 700, fontSize: 14,
            }}>+ Nova OLT</button>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 16 }}>
            {olts.length === 0 ? (
              <div style={{ gridColumn: '1/-1', textAlign: 'center', padding: 60, color: '#9ca3af', background: '#fff', borderRadius: 16 }}>
                <div style={{ fontSize: 40, marginBottom: 8 }}>📡</div>
                Nenhuma OLT cadastrada. Clique em "+ Nova OLT" para começar.
              </div>
            ) : olts.map(olt => (
              <div key={olt.id} style={{
                background: '#fff', borderRadius: 16, padding: 20,
                boxShadow: '0 2px 12px rgba(0,0,0,0.07)', border: '1px solid #e5e7eb',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
                  <div>
                    <div style={{ fontWeight: 800, fontSize: 16, color: '#111827' }}>{olt.nome}</div>
                    <div style={{ fontSize: 12, color: '#6b7280', fontFamily: 'monospace' }}>{olt.ip}:{olt.porta_snmp}</div>
                  </div>
                  <span style={{
                    padding: '3px 10px', borderRadius: 99, fontSize: 11, fontWeight: 700,
                    background: olt.is_active ? '#d1fae5' : '#fee2e2',
                    color: olt.is_active ? '#059669' : '#ef4444',
                  }}>{olt.is_active ? 'Ativa' : 'Inativa'}</span>
                </div>
                {[
                  ['Fabricante', olt.fabricante],
                  ['Modelo', olt.modelo],
                  ['Localização', olt.localizacao],
                ].filter(([, v]) => v).map(([k, v]) => (
                  <div key={String(k)} style={{ fontSize: 13, color: '#6b7280', marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, color: '#374151' }}>{k}:</span> {v}
                  </div>
                ))}

                <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
                  <button onClick={() => setOltModal({ open: true, olt })} style={{
                    flex: 1, background: '#f3f4f6', color: '#374151', border: 'none', borderRadius: 8,
                    padding: '8px', cursor: 'pointer', fontWeight: 600, fontSize: 13,
                  }}>✏️ Editar</button>
                  <button onClick={() => handleDeleteOLT(olt.id)} style={{
                    flex: 1, background: '#fee2e2', color: '#ef4444', border: 'none', borderRadius: 8,
                    padding: '8px', cursor: 'pointer', fontWeight: 600, fontSize: 13,
                  }}>🗑️ Remover</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {infraTab === 'ctos' && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <div style={{ fontWeight: 700, color: '#374151', fontSize: 15 }}>CTOs Cadastradas — {ctos.length}</div>
            <button onClick={() => setCtoModal({ open: true, cto: null })} style={{
              background: '#4f46e5', color: '#fff', border: 'none', borderRadius: 10,
              padding: '10px 18px', cursor: 'pointer', fontWeight: 700, fontSize: 14,
            }}>+ Nova CTO</button>
          </div>
          <div style={{ background: '#fff', borderRadius: 16, boxShadow: '0 2px 12px rgba(0,0,0,0.07)', overflow: 'hidden' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ background: '#f9fafb' }}>
                  {['Nome', 'OLT', 'PON', 'Splitter', 'Capacidade', 'Endereço', 'GPS', 'Ações'].map(h => (
                    <th key={h} style={{ padding: '12px 14px', textAlign: 'left', color: '#6b7280', fontWeight: 700, fontSize: 12, borderBottom: '1px solid #e5e7eb' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {ctos.length === 0 ? (
                  <tr><td colSpan={8} style={{ padding: 40, textAlign: 'center', color: '#9ca3af' }}>
                    <div style={{ fontSize: 32, marginBottom: 8 }}>📦</div>
                    Nenhuma CTO cadastrada
                  </td></tr>
                ) : ctos.map(cto => (
                  <tr key={cto.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                    <td style={{ padding: '12px 14px', fontWeight: 700, color: '#111827' }}>{cto.nome}</td>
                    <td style={{ padding: '12px 14px', color: '#374151' }}>{cto.olt_nome || '—'}</td>
                    <td style={{ padding: '12px 14px', fontFamily: 'monospace', color: '#374151' }}>{cto.porta_pon || '—'}</td>
                    <td style={{ padding: '12px 14px', color: '#374151' }}>{cto.splitter_ratio || '—'}</td>
                    <td style={{ padding: '12px 14px', color: '#374151' }}>{cto.capacidade || '—'}</td>
                    <td style={{ padding: '12px 14px', color: '#374151', maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{cto.endereco || '—'}</td>
                    <td style={{ padding: '12px 14px', fontFamily: 'monospace', fontSize: 11, color: '#9ca3af' }}>{cto.coordenadas_gps || '—'}</td>
                    <td style={{ padding: '12px 14px', display: 'flex', gap: 6 }}>
                      <button onClick={() => setCtoModal({ open: true, cto })} style={{
                        background: '#f3f4f6', color: '#374151', border: 'none', borderRadius: 7,
                        padding: '6px 10px', cursor: 'pointer', fontWeight: 600, fontSize: 12,
                      }}>✏️</button>
                      <button onClick={() => handleDeleteCTO(cto.id)} style={{
                        background: '#fee2e2', color: '#ef4444', border: 'none', borderRadius: 7,
                        padding: '6px 10px', cursor: 'pointer', fontWeight: 600, fontSize: 12,
                      }}>🗑️</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );

  const renderHistorico = () => (
    <div>
      <div style={{ background: '#fff', borderRadius: 16, padding: 32, boxShadow: '0 2px 12px rgba(0,0,0,0.07)' }}>
        <h3 style={{ fontWeight: 800, color: '#374151', marginBottom: 16 }}>📈 Histórico e Relatórios</h3>
        <p style={{ color: '#6b7280', fontSize: 14 }}>
          Para consultar o histórico de uma ONU específica, acesse a aba <strong>ONUs</strong> e clique em <strong>Detalhes</strong> na ONU desejada.
          O histórico das últimas 24 horas é exibido no modal com gráfico de disponibilidade.
        </p>
        <div style={{ marginTop: 24, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16 }}>
          {[
            { icon: '📊', title: 'Disponibilidade', desc: `${dashboard?.disponibilidade_percentual?.toFixed(1) ?? '—'}% das ONUs online agora` },
            { icon: '🔴', title: 'Alertas Ativos', desc: `${alertas.length} ONU${alertas.length !== 1 ? 's' : ''} com problema` },
            { icon: '📡', title: 'Total ONUs', desc: `${dashboard?.total_onus ?? '—'} ONUs monitoradas` },
            { icon: '⏱️', title: 'Intervalo Polling', desc: 'A cada 5 minutos (automático)' },
          ].map(({ icon, title, desc }) => (
            <div key={title} style={{ background: '#f9fafb', borderRadius: 12, padding: '18px 20px', border: '1px solid #e5e7eb' }}>
              <div style={{ fontSize: 28, marginBottom: 8 }}>{icon}</div>
              <div style={{ fontWeight: 700, color: '#374151', marginBottom: 4 }}>{title}</div>
              <div style={{ fontSize: 13, color: '#6b7280' }}>{desc}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  const createOnuIcon = (status: string) => {
    const colors = {
      ONLINE: '#10b981',
      OFFLINE: '#ef4444',
      DEGRADADO: '#f59e0b',
      DESCONHECIDO: '#6b7280',
    };
    const color = colors[status as keyof typeof colors] || colors.DESCONHECIDO;
    return L.divIcon({
      html: `<div style="display: flex; justify-content: center; align-items: center; width: 24px; height: 24px; background-color: ${color}; border-radius: 50% 50% 50% 0; transform: rotate(-45deg); border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);">
              <div style="width: 7px; height: 7px; background-color: white; border-radius: 50%; transform: rotate(45deg);"></div>
            </div>`,
      className: 'custom-onu-pin',
      iconSize: [24, 24],
      iconAnchor: [12, 24]
    });
  };

  const renderMapa = () => {
    let center: [number, number] = [-23.5505, -46.6333];
    let foundCenter = false;

    for (const onu of onus) {
      const pc = parseCoords(onu.coordenadas_gps);
      if (pc) {
        center = pc;
        foundCenter = true;
        break;
      }
    }

    if (!foundCenter) {
      for (const cto of ctos) {
        const pc = parseCoords(cto.coordenadas_gps);
        if (pc) {
          center = pc;
          foundCenter = true;
          break;
        }
      }
    }

    return (
      <div style={{ background: '#fff', borderRadius: 20, padding: 24, boxShadow: '0 4px 20px rgba(0,0,0,0.05)', display: 'flex', flexDirection: 'column', gap: 20 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h3 style={{ fontSize: 18, fontWeight: 800, margin: 0, color: '#111827' }}>📍 Mapa de Status das ONUs</h3>
            <p style={{ margin: '4px 0 0', fontSize: 13, color: '#6b7280' }}>
              Localização geográfica dos clientes e CTOs com status de conectividade em tempo real.
            </p>
          </div>
          <div style={{ display: 'flex', gap: 12, fontSize: 12, fontWeight: 700 }}>
            <span style={{ color: '#10b981' }}>🟢 Online</span>
            <span style={{ color: '#ef4444' }}>🔴 Offline</span>
            <span style={{ color: '#f59e0b' }}>🟡 Degradado</span>
            <span style={{ color: '#6b7280' }}>⚪ Desconhecido</span>
            <span style={{ color: '#8b5cf6' }}>📦 CTO</span>
          </div>
        </div>

        <div style={{ height: '650px', borderRadius: 14, overflow: 'hidden', border: '1px solid #e5e7eb', position: 'relative', zIndex: 1 }}>
          <MapContainer center={center} zoom={13} style={{ height: '100%', width: '100%' }}>
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            <ChangeMapCenter center={center} zoom={13} />

            {/* Renderizar ONUs */}
            {onus.map(onu => {
              const pc = parseCoords(onu.coordenadas_gps);
              if (!pc) return null;
              
              const cfg = STATUS_CONFIG[onu.status as keyof typeof STATUS_CONFIG] || STATUS_CONFIG.DESCONHECIDO;
              
              return (
                <Marker key={`onu-${onu.contrato_id}`} position={pc} icon={createOnuIcon(onu.status)}>
                  <Popup>
                    <div style={{ fontFamily: 'Inter, system-ui, sans-serif', minWidth: 200 }}>
                      <div style={{ fontWeight: 800, fontSize: 14, color: '#111827', marginBottom: 4 }}>{onu.cliente_nome}</div>
                      <div style={{ display: 'flex', gap: 6, alignItems: 'center', marginBottom: 8 }}>
                        <span style={{
                          padding: '2px 8px', borderRadius: 99, fontSize: 10, fontWeight: 700,
                          background: cfg.bg, color: cfg.color
                        }}>{cfg.label}</span>
                        {onu.latencia_ms != null && (
                          <span style={{ fontSize: 11, color: '#4f46e5', fontWeight: 600 }}>ping: {onu.latencia_ms.toFixed(1)} ms</span>
                        )}
                      </div>
                      
                      <div style={{ fontSize: 12, color: '#4b5563', display: 'flex', flexDirection: 'column', gap: 3 }}>
                        <div><strong>Contrato:</strong> {onu.numero_contrato || '—'}</div>
                        <div><strong>IP:</strong> <span style={{ fontFamily: 'monospace' }}>{onu.assigned_ip || '—'}</span></div>
                        <div><strong>OLT:</strong> {onu.olt_nome || '—'} (Porta {onu.olt_pon || '—'})</div>
                        <div><strong>CTO:</strong> {onu.cto_nome || '—'} (Porta {onu.cto_porta || '—'})</div>
                        <div><strong>Última verif:</strong> {formatDate(onu.ultima_verificacao)}</div>
                      </div>

                      <button 
                        onClick={() => setSelectedONU(onu)}
                        style={{
                          width: '100%', marginTop: 10, padding: '6px', background: '#4f46e5',
                          color: '#fff', border: 'none', borderRadius: 6, fontWeight: 700,
                          fontSize: 11, cursor: 'pointer'
                        }}
                      >
                        Ver Detalhes / Gráfico
                      </button>
                    </div>
                  </Popup>
                </Marker>
              );
            })}

            {/* Renderizar CTOs */}
            {ctos.map(cto => {
              const pc = parseCoords(cto.coordenadas_gps);
              if (!pc) return null;

              const ctoMarkerIcon = L.divIcon({
                html: `<div style="display: flex; justify-content: center; align-items: center; width: 28px; height: 28px; background-color: #8b5cf6; border-radius: 4px; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3); font-size: 14px; color: white; font-weight: bold; transform: scale(1.15);">
                        📦
                      </div>`,
                className: 'custom-cto-pin',
                iconSize: [28, 28],
                iconAnchor: [14, 14]
              });

              return (
                <Marker key={`cto-${cto.id}`} position={pc} icon={ctoMarkerIcon}>
                  <Popup>
                    <div style={{ fontFamily: 'Inter, system-ui, sans-serif', minWidth: 180 }}>
                      <div style={{ fontWeight: 800, fontSize: 13, color: '#7c3aed', marginBottom: 2 }}>📦 {cto.nome}</div>
                      <div style={{ fontSize: 11, color: '#6b7280', marginBottom: 6 }}>Caixa de Atendimento</div>
                      
                      <div style={{ fontSize: 12, color: '#4b5563', display: 'flex', flexDirection: 'column', gap: 3 }}>
                        <div><strong>OLT:</strong> {cto.olt_nome || '—'} (Porta {cto.porta_pon || '—'})</div>
                        <div><strong>Splitter:</strong> {cto.splitter_ratio || '—'}</div>
                        <div><strong>Portas ocupadas:</strong> {cto.capacidade || 16} portas</div>
                        {cto.endereco && <div style={{ fontSize: 11, color: '#6b7280', marginTop: 4 }}>📍 {cto.endereco}</div>}
                      </div>
                    </div>
                  </Popup>
                </Marker>
              );
            })}
          </MapContainer>
        </div>
      </div>
    );
  };

  // ============================================================
  // RENDER PRINCIPAL
  // ============================================================
  const tabs = [
    { key: 'dashboard', label: '📊 Dashboard' },
    { key: 'onts', label: '📡 ONUs / Clientes' },
    { key: 'mapa', label: '📍 Mapa de Status' },
    { key: 'infra', label: '🏗️ Infraestrutura' },
    { key: 'historico', label: '📈 Histórico' },
  ];

  return (
    <div style={{ fontFamily: 'Inter, Roboto, system-ui, sans-serif', minHeight: '100%' }}>
      {/* Header */}
      <div style={{
        background: 'linear-gradient(135deg, #312e81 0%, #4f46e5 50%, #7c3aed 100%)',
        borderRadius: 20, padding: '28px 32px', marginBottom: 28, color: '#fff',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        boxShadow: '0 8px 32px rgba(79,70,229,0.3)',
      }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 26, fontWeight: 900, letterSpacing: -0.5 }}>
            📡 Monitoramento FTTH
          </h1>
          <p style={{ margin: '6px 0 0', opacity: 0.8, fontSize: 14 }}>
            Status em tempo real das ONUs, OLTs e CTOs da rede óptica
          </p>
        </div>
        <div style={{ textAlign: 'right' }}>
          {dashboard && (
            <>
              <div style={{ fontSize: 36, fontWeight: 900 }}>{dashboard.disponibilidade_percentual.toFixed(1)}%</div>
              <div style={{ fontSize: 12, opacity: 0.8 }}>disponibilidade</div>
            </>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 24, background: '#f3f4f6', borderRadius: 14, padding: 4, width: 'fit-content' }}>
        {tabs.map(({ key, label }) => (
          <button key={key} onClick={() => setActiveTab(key as any)} style={{
            padding: '10px 20px', borderRadius: 10, border: 'none', cursor: 'pointer',
            fontWeight: 700, fontSize: 14, transition: 'all 0.2s',
            background: activeTab === key ? '#fff' : 'transparent',
            color: activeTab === key ? '#4f46e5' : '#6b7280',
            boxShadow: activeTab === key ? '0 2px 8px rgba(0,0,0,0.1)' : 'none',
          }}>{label}</button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'dashboard' && renderDashboard()}
      {activeTab === 'onts' && renderONTs()}
      {activeTab === 'mapa' && renderMapa()}
      {activeTab === 'infra' && renderInfra()}
      {activeTab === 'historico' && renderHistorico()}

      {/* Modais */}
      {selectedONU && (
        <ONUDetailModal
          onu={selectedONU}
          onClose={() => setSelectedONU(null)}
          token={token || ''}
          empresaId={empresaId}
        />
      )}
      {oltModal.open && (
        <OLTModal
          olt={oltModal.olt}
          onClose={() => setOltModal({ open: false })}
          onSave={handleSaveOLT}
          saving={oltSaving}
        />
      )}
      {ctoModal.open && (
        <CTOModal
          cto={ctoModal.cto}
          olts={olts}
          ctos={ctos}
          onClose={() => setCtoModal({ open: false })}
          onSave={handleSaveCTO}
          saving={ctoSaving}
        />
      )}
    </div>
  );
};

export default FTTHMonitor;
