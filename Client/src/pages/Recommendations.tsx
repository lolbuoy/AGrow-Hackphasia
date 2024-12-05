import React, { useEffect, useState } from "react"
import { Link } from "wouter"
import useMqtt from "../mqtt"

export default function Recommendations() {
	const [data, setData] = useState([])
	const [averageValues, setAverage] = useState({})
	const [cropsDetailed, setCropsDetailed] = useState({})
	const roverId = localStorage.getItem("rover_id") ?? "255"
	const [redisLoading, setRedisLoading] = useState(true)
	const [redisData, setRedisData] = useState(null)

	const {
		publish,
		loading: mqttLoading,
		error,
	} = useMqtt({
		brokerUrl: "ws://100.109.46.43",
		port: 9001,
		onMessageArrived: (topic, message) => {
			try {
				const jsonStuff = JSON.parse(message) ?? {}
				const keys = Object.keys(jsonStuff)

				if (keys.includes("crops")) {
					setData(jsonStuff["crops"])
				}
				if (keys.includes("avg_values")) {
					setAverage(jsonStuff["avg_values"])
				}

				localStorage.setItem("cropdata", message)

				setLoading(false)
			} catch (err) {
				console.error("Message parsing error:", err)
			}
		},
		channels: [`ai/crops/${roverId}/response`],
	})

	const [loading, setLoading] = useState(true)

	const finalLoading = redisLoading || loading || mqttLoading

	useEffect(() => {
		if (!redisLoading) {
			if (mqttLoading) {
				return
			}
			publish(`ai/crops/${roverId}/request`, JSON.stringify(redisData))
		} else {
			;(async () => {
				const res = await fetch(`http://localhost:8826/data/${roverId}`, {
					method: "GET",
				})
				if (!res.ok) {
					alert(res.statusText)
					return
				}
				setRedisData(await res.json())
				setRedisLoading(false)
			})()
		}
	}, [redisLoading, mqttLoading])

	if (loading) {
		return (
			<>
				<h1>Loading...</h1>
			</>
		)
	}

	return (
		<>
			<div className="text-red-800 underline">
				<Link to="/zone">Back</Link>
			</div>
			<div className="h-4"></div>
			<h1>Crop Recommendations</h1>
			<div className="h-8"></div>
			<div className="flex flex-row justify-between items-center gap-2">
				<h3 className="text-3xl font-light uppercase">Soil Conditions</h3>
				<div className="flex flex-col gap-0 text-right">
					<p>
						<strong>Temperature</strong> {(averageValues.temperature ?? 0).toFixed(2)}ºC
					</p>
					<p>
						<strong>Rainfall</strong> {(averageValues.rainfall ?? 0).toFixed(2)} mm per year
					</p>
					<p>
						<strong>pH Level</strong> {(averageValues.ph ?? 0).toFixed(2)}
					</p>
					<p>
						<strong>Nitrogen</strong> {(averageValues.nitrogen ?? 0).toFixed(2)} ppm
					</p>
					<p>
						<strong>Phosphorus</strong> {(averageValues.phosphorus ?? 0).toFixed(2)} ppm
					</p>
					<p>
						<strong>Potassium</strong> {(averageValues.potassium ?? 0).toFixed(2)} ppm
					</p>
				</div>
			</div>
			<div className="h-12"></div>

			<div className="flex flex-col gap-8">
				{data.map((e) => (
					<Link to={`plan/${e}`}>
						<div className=" p-8 bg-white border border-green-300 rounded-md shadow-md">
							<h3 className="text-4xl font-bold">{e}</h3>
							{/* <div className="h-2"></div> */}
							{/* <p>{e.details.replace(/br/g, "<br /><br />")}</p> */}
						</div>
					</Link>
				))}
			</div>
		</>
	)
}
