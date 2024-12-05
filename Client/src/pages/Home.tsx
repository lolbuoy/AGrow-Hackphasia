import React from "react"
import { Link } from "wouter"

export default function Home() {
	return (
		<>
			<div className="full-center">
				<h1>Click to analyse your field</h1>
				<p></p>
				<div className="underline text-green-600 text-lg">
					<Link to="/zone">Set a zone</Link>
				</div>
			</div>
		</>
	)
}
