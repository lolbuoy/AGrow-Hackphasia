import React from "react"
import { Link } from "wouter"

function toTitleCase(str) {
	return str.replace(/\w\S*/g, (text) => text.charAt(0).toUpperCase() + text.substring(1).toLowerCase())
}

export default function Plan({ crop }) {
	const details = (JSON.parse(localStorage.getItem("cropdata") ?? "{}")["cropsdetailed"] ?? {})[crop] ?? "-"

	return (
		<>
			<div className="text-red-800 underline">
				<Link to="/recommendations">Back</Link>
			</div>
			<div className="h-4"></div>
			<h1>Growth Plan for {toTitleCase(crop)}</h1>
			<div className="h-4"></div>
			<p
				dangerouslySetInnerHTML={{
					__html: details,
				}}
			/>
		</>
	)
}
