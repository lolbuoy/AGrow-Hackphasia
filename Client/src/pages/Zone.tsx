import React, { useState } from "react"
import { MapContainer, TileLayer, Polygon, useMapEvents, Marker } from "react-leaflet"
import "leaflet/dist/leaflet.css"
import { useLocation } from "wouter"

export default function Zone() {
	const [points, setPoints] = useState([])
	const [location, setLocation] = useLocation()

	function MapClickHandler() {
		useMapEvents({
			click(e) {
				if (points.length < 5) {
					const { lat, lng } = e.latlng
					setPoints([...points, [lat, lng]])
				} else {
					const { lat, lng } = e.latlng
					setPoints([...points.slice(1), [lat, lng]])
				}
			},
		})
		return null
	}

	function onSelect() {
		localStorage.setItem("points", JSON.stringify(points))
		setLocation("/fetching")
	}

	return (
		<>
			<h1>Set a Zone</h1>
			<p>Click on the map to define a zone with 5 points.</p>
			<div className="h-2"></div>
			<MapContainer
				center={[12, 77]} // Default center
				zoom={13}
				// bounds={{
				// 	center: [12, 77],
				// }}
				style={{ height: "80%", width: "100%" }}
			>
				<TileLayer
					attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
					url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
				/>
				<MapClickHandler />
				{points.map((point) => (
					<Marker position={point}>
						<p>.</p>
					</Marker>
				))}
				{points.length === 5 && <Polygon positions={points} pathOptions={{ color: "blue" }} />}
			</MapContainer>
			<div className="h-4"></div>
			<div className="flex flex-row justify-end">
				{points.length === 5 ? (
					<button
						onClick={onSelect}
						className="bg-green-600 text-white p-4 shadow-md rounded-md font-bold min-w-32"
					>
						Select
					</button>
				) : (
					<p>Select 5 points first</p>
				)}
			</div>
		</>
	)
}
