import { CircleMarker, MapContainer, Popup, TileLayer } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'

const NODE_COORDS = {
  "HSR Layout": [12.9121, 77.6446],
  "Silk Board": [12.9175, 77.6234],
  "Koramangala": [12.9352, 77.6245],
  "Bellandur": [12.9304, 77.6784],
  "Marathahalli": [12.9569, 77.7011],
}

function TrafficMap({ result }) {
  const epicenterLocation = result?.extraction?.location
  const epicenterCoords =
    epicenterLocation && NODE_COORDS[epicenterLocation]
      ? NODE_COORDS[epicenterLocation]
      : null

  return (
    <MapContainer
      center={[12.9300, 77.6400]}
      zoom={13}
      className="h-full w-full rounded-xl z-0"
      scrollWheelZoom
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
      />

      {epicenterCoords && (
        <CircleMarker
          center={epicenterCoords}
          radius={20}
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

      {result?.ripple_effect?.map((item, index) => {
        const coords = NODE_COORDS[item.node]
        if (!coords) return null

        return (
          <CircleMarker
            key={`${item.node}-${index}`}
            center={coords}
            radius={15}
            pathOptions={{
              color: '#f97316',
              fillColor: '#f97316',
              fillOpacity: 0.55,
              weight: 2,
            }}
          >
            <Popup>
              <strong>{item.node}</strong>
              <br />
              Secondary delay: {item.secondary_delay_mins} min
            </Popup>
          </CircleMarker>
        )
      })}
    </MapContainer>
  )
}

export default TrafficMap
