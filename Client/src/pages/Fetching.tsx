import React, { useEffect, useState, useCallback } from "react"
import { Link, useLocation } from "wouter"
import { MapContainer, TileLayer, Polyline, Marker, Popup, useMap } from "react-leaflet"
import "leaflet/dist/leaflet.css"
import L from "leaflet"
import useMqtt from "../mqtt"

// Custom marker icons
const statusColors = {
	unknown: "gray",
	idle: "blue",
	moving: "green",
	error: "red",
	completed: "purple",
}

const getMarkerIcon = (status) => {
	return L.divIcon({
		className: "custom-div-icon",
		html: `<div style="background-color:${statusColors[status] || "gray"};" class="marker-pin"></div>`,
		iconSize: [30, 42],
		iconAnchor: [15, 42],
	})
}

// Persistent Map State Component
function PersistentMapState() {
	const map = useMap()

	// Save map state to localStorage when it moves
	useEffect(() => {
		const saveMapState = () => {
			const center = map.getCenter()
			const zoom = map.getZoom()
			localStorage.setItem(
				"mapState",
				JSON.stringify({
					center: [center.lat, center.lng],
					zoom,
				})
			)
		}

		map.on("moveend", saveMapState)
		map.on("zoomend", saveMapState)

		return () => {
			map.off("moveend", saveMapState)
			map.off("zoomend", saveMapState)
		}
	}, [map])

	return null
}

export default function Fetching() {
	const [location, setLocation] = useLocation()
	const [roverId, setRoverId] = useState("255")
	const [roverState, setRoverState] = useState({
		status: "unknown",
		latlng: [0, 0],
		waypoints: [],
	})

	// Retrieve saved map state or use default
	const getSavedMapState = useCallback(() => {
		const savedState = localStorage.getItem("mapState")
		if (savedState) {
			try {
				return JSON.parse(savedState)
			} catch {
				return null
			}
		}
		return null
	}, [])

	// Determine map center and zoom
	const mapState = getSavedMapState() || {
		center:
			roverState.latlng[0] !== 0
				? roverState.latlng
				: roverState.waypoints.length > 0
				? roverState.waypoints[0]
				: [12, 77],
		zoom: 15,
	}

	const { publish, loading, error } = useMqtt({
		brokerUrl: "ws://100.109.46.43",
		port: 9001,
		onMessageArrived: (topic, message) => {
			try {
				const parsedMessage = JSON.parse(message)
				if (!(parsedMessage.status && parsedMessage.latlng)) {
					return
				}
				if (["status", "latlng", "waypoints"].every((key) => key in parsedMessage)) {
					setRoverState(parsedMessage)
				}
			} catch (err) {
				console.error("Message parsing error:", err)
			}
		},
		channels: [`ground/${roverId}/telemetry`],
	})

	useEffect(() => {
		localStorage.setItem("rover_id", "255")
		setRoverId("255")
	}, [])

	if (!localStorage.getItem("points")) {
		setLocation("/zone")
		return null
	}

	function handleStart() {
		publish(`ground/${roverId}/plan`, localStorage.getItem("points"))
	}

	return (
		<div className="flex flex-col gap-4 p-4">
			<div className="text-red-800 underline">
				<Link to="/zone">Back</Link>
			</div>
			<div className="h-4"></div>
			<h1>Rover Status</h1>

			{loading ? <p>Connecting</p> : ""}

			{/* Status Label */}
			<div
				className={`p-2 rounded text-center font-semibold ${
					statusColors[roverState.status] || "bg-gray-200"
				} text-black`}
			>
				Status: {roverState.status.toUpperCase()}
			</div>

            {/* {JSON.stringify(roverState.latlng)}
            {JSON.stringify(roverState.latlng[0] !== 0)} */}

			{/* Leaflet Map */}
			<MapContainer center={mapState.center} zoom={mapState.zoom} style={{ height: "400px", width: "100%" }}>
				{/* <PersistentMapState /> */}

				<TileLayer
					attribution="&copy; OpenStreetMap contributors"
					url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
				/>

				{/* Current Location Marker */}
				{roverState.latlng[0] !== 0 ? (
					<Marker position={roverState.latlng}>
                        <p>.</p>
						<Popup>Current Location</Popup>
					</Marker>
				) : (
					""
				)}

				{/* Waypoints */}
				{roverState.waypoints.map((waypoint, index) => (
					<Marker key={index} position={waypoint} icon={getMarkerIcon("idle")}>
						<Popup>Waypoint {index + 1}</Popup>
					</Marker>
				))}

				{/* Polyline connecting waypoints */}
				{roverState.waypoints.length > 1 && (
					<Polyline positions={roverState.waypoints} color="blue" weight={3} opacity={0.7} />
				)}
			</MapContainer>

			<div className="flex flex-row justify-between items-center gap-4">
				{/* Start Button */}
				<button onClick={handleStart} className="bg-green-700 text-white p-2 px-6 rounded">
					Start
				</button>
				<Link to="/recommendations">
					<button className="bg-green-700 text-white p-2 px-6 rounded">Calculate</button>
				</Link>
			</div>
		</div>
	)
}
