import { CircleMarker, MapContainer, Popup, Polyline, TileLayer } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'

const NODE_COORDS = {
  "HSR Layout": [12.9121, 77.6446],
  "Silk Board": [12.9175, 77.6234],
  "Koramangala": [12.9352, 77.6245],
  "Bellandur": [12.9304, 77.6784],
  "Marathahalli": [12.9569, 77.7011],
  "Agara Signal": [12.9198, 77.6457],
  "HSR Junction": [12.9121, 77.6446],
  "Bellandur Gate": [12.9249, 77.6678],
  "Bommanahalli Junction": [12.8982, 77.6258],
  "Adugodi Signal": [12.9440, 77.6117],
  "Madiwala": [12.9173, 77.6200],
  "Goraguntepalya": [13.0292, 77.5490],
  "Jalahalli Cross": [13.0357, 77.5258],
  "Hope Farm Junction": [12.9955, 77.7590],
  "ITPL Main Gate": [12.9863, 77.7365],
  "Silk Board Flyover Entry": [12.9178, 77.6230],
  "HSR Flyover Ramp": [12.9124, 77.6440],
  "Bellandur Gate Entry": [12.9270, 77.6710],
}

function TrafficMap({ result, timelineMinutes = 60 }) {
  const epicenterLocation = result?.extraction?.location
  const routeOptimization = result?.route_optimization
  const actionPlan = result?.action_plan
  let epicenterCoords = null

  if (epicenterLocation && NODE_COORDS[epicenterLocation]) {
    epicenterCoords = NODE_COORDS[epicenterLocation]
  } else if (routeOptimization?.epicenter_coordinates) {
    epicenterCoords = routeOptimization.epicenter_coordinates
  }

  const routeLines = routeOptimization?.route_lines ?? []
  const impactZones = routeOptimization?.impact_zones ?? []
  const rippleZones = result?.ripple_effect ?? []
  const blockedRoads = routeOptimization?.recommended_closures ?? []
  const deploymentZones = actionPlan?.deployment_zones ?? []

  const visibleImpactZones = timelineMinutes === 0
    ? impactZones.filter((zone) => zone.horizon_mins === 15)
    : impactZones.filter((zone) => !zone.horizon_mins || zone.horizon_mins <= timelineMinutes)

  const visibleRippleZones = timelineMinutes === 0
    ? []
    : rippleZones.filter((zone) => !zone.horizon_mins || zone.horizon_mins <= timelineMinutes)

  const colorForRipple = (horizon) => {
    if (horizon >= 60) return '#fde047'
    if (horizon >= 45) return '#facc15'
    if (horizon >= 30) return '#f59e0b'
    return '#fb923c'
  }

  return (
    <div className="relative h-full w-full">
      <MapContainer
        center={epicenterCoords ?? [12.9300, 77.6400]}
        zoom={12.8}
        className="h-full w-full rounded-xl z-0"
        scrollWheelZoom
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        />

        {visibleImpactZones.map((zone) => (
          <CircleMarker
            key={zone.label}
            center={zone.coordinates}
            radius={zone.radius_meters / 80}
            pathOptions={{
              color: zone.horizon_mins === 15 ? '#f97316' : zone.color,
              fillColor: zone.horizon_mins === 15 ? '#f97316' : zone.color,
              fillOpacity: 0.16,
              weight: 2,
            }}
          >
            <Popup>
              <strong>{zone.label}</strong>
            </Popup>
          </CircleMarker>
        ))}

        {visibleRippleZones.map((item, index) => {
          const coords = item.coordinates || epicenterCoords
          if (!coords) return null
          return (
            <CircleMarker
              key={`${item.label}-${index}`}
              center={coords}
              radius={Math.max(10, (item.radius_meters || 800) / 120)}
              pathOptions={{
                color: colorForRipple(item.horizon_mins),
                fillColor: colorForRipple(item.horizon_mins),
                fillOpacity: 0.12,
                weight: 2,
              }}
            >
              <Popup>
                <strong>{item.node}</strong>
                <br />
                {item.horizon_mins || 0} min ripple
                <br />
                Delay: {item.secondary_delay_mins} min
              </Popup>
            </CircleMarker>
          )
        })}

        {epicenterCoords && (
          <CircleMarker
            center={epicenterCoords}
            radius={22}
            pathOptions={{
              color: '#ef4444',
              fillColor: '#ef4444',
              fillOpacity: 0.6,
              weight: 2,
            }}
          >
            <Popup>
              <strong>Epicenter: {epicenterLocation}</strong>
              <br />
              Incident: {result.extraction.incident_type}
            </Popup>
          </CircleMarker>
        )}

        {routeLines.map((route) => (
          <Polyline
            key={route.label}
            positions={route.coordinates}
            pathOptions={{
              color: route.color,
              weight: 5,
              opacity: 0.92,
            }}
          >
            <Popup>{route.label}</Popup>
          </Polyline>
        ))}

        {blockedRoads.map((closure) => {
          const coords = NODE_COORDS[closure]
          if (!coords) return null
          return (
            <CircleMarker
              key={closure}
              center={coords}
              radius={14}
              pathOptions={{
                color: '#ef4444',
                fillColor: '#ef4444',
                fillOpacity: 0.45,
                weight: 2,
              }}
            >
              <Popup>
                <strong>Blocked Road</strong>
                <br />
                {closure}
              </Popup>
            </CircleMarker>
          )
        })}

        {deploymentZones.map((zone) => {
          const coords = NODE_COORDS[zone]
          if (!coords) return null
          return (
            <CircleMarker
              key={`deploy-${zone}`}
              center={coords}
              radius={12}
              pathOptions={{
                color: '#22c55e',
                fillColor: '#22c55e',
                fillOpacity: 0.45,
                weight: 2,
              }}
            >
              <Popup>
                <strong>Police Deployment</strong>
                <br />
                {zone}
              </Popup>
            </CircleMarker>
          )
        })}
      </MapContainer>

      <div className="pointer-events-none absolute left-3 top-3 rounded-2xl border border-white/10 bg-slate-950/80 px-3 py-2 text-[11px] uppercase tracking-[0.18em] text-slate-200 shadow-lg shadow-black/30 backdrop-blur-xl">
        Timeline: {timelineMinutes === 0 ? 'Current' : `${timelineMinutes} min`}
      </div>

      <div className="absolute bottom-3 left-3 rounded-2xl border border-white/10 bg-slate-950/80 p-3 text-xs text-slate-200 shadow-lg shadow-black/30 backdrop-blur-xl">
        <p className="mb-2 text-[10px] uppercase tracking-[0.2em] text-slate-400">Legend</p>
        <div className="grid gap-1.5">
          <LegendItem color="#ef4444" label="Blocked Road" />
          <LegendItem color="#f59e0b" label="Congestion Zone" />
          <LegendItem color="#fde047" label="Ripple Zone" />
          <LegendItem color="#3b82f6" label="Diversion Route" />
          <LegendItem color="#22c55e" label="Police Deployment" />
        </div>
      </div>
    </div>
  )
}

function LegendItem({ color, label }) {
  return (
    <div className="flex items-center gap-2">
      <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: color }} />
      <span>{label}</span>
    </div>
  )
}

export default TrafficMap
