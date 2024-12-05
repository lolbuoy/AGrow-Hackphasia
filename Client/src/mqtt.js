import mqtt from "mqtt"
import { useEffect, useRef, useState, useCallback } from "react"

export default function useMqtt({
	brokerUrl = "ws://localhost",
	port = 9001,
	options = {},
	channels,
	onMessageArrived,
}) {
	const [error, setError] = useState(null)
	const [loading, setLoading] = useState(true)
	const [isConnected, setIsConnected] = useState(false)

	const mqttClientRef = useRef(null)
	const reconnectTimerRef = useRef(null)

	const fullBrokerUrl = `${brokerUrl}:${port}`

	const connectClient = useCallback(() => {
		// Clean up any existing connection
		if (mqttClientRef.current) {
			mqttClientRef.current.end(true)
		}

		// Default connection options
		const defaultOptions = {
			reconnectPeriod: 0, // Disable automatic reconnections
			clean: true,
			connectTimeout: 4000,
			...options,
		}

		try {
			const client = mqtt.connect(fullBrokerUrl, defaultOptions)
			mqttClientRef.current = client

			client.on("connect", () => {
				setLoading(false)
				setIsConnected(true)
				setError(null)
				console.log("Connected")

				// Subscribe to channels
				client.subscribe(channels, (err, granted) => {
					if (err) {
						console.error("Subscription error:", err)
						setError(err.message)
					} else {
						console.log("Subscribed to channels:", granted.map((g) => g.topic).join(", "))
					}
				})
			})

			client.on("message", (topic, message) => {
				const msgString = message.toString()
				onMessageArrived(topic, msgString)
			})

			client.on("error", (err) => {
				console.error("MQTT error:", err)
				setError(err.message)
				setIsConnected(false)
			})

			client.on("close", () => {
				console.log("Connection closed.")
				setError("Connection closed")
				setLoading(true)
				setIsConnected(false)
				scheduleReconnect()
			})
		} catch (err) {
			console.error("Failed to connect:", err)
			setError(String(err))
			setLoading(false)
			scheduleReconnect()
		}
	}, [])

	const scheduleReconnect = useCallback(() => {
		// Clear any existing reconnect timer
		if (reconnectTimerRef.current) {
			clearTimeout(reconnectTimerRef.current)
		}
		console.log("Disconnected, soon reconnecting")

		// Schedule a reconnection attempt
		reconnectTimerRef.current = setTimeout(() => {
			console.log("Attempting manual reconnection...")
			connectClient()
		}, 5000) // Retry after 5 seconds
	}, [connectClient])

	const publish = useCallback((topic, message, options = {}) => {
		const client = mqttClientRef.current
		if (client && client.connected) {
			client.publish(topic, message, options, (err) => {
				if (err) {
					console.error("Publish error:", err)
				} else {
					console.log("Published:", topic, message)
				}
			})
		} else {
			console.error("Cannot publish, client not connected.")
		}
	}, [])

	// Initial connection and cleanup
	useEffect(() => {
		connectClient()

		// Cleanup function
		return () => {
			if (mqttClientRef.current) {
				mqttClientRef.current.end(true)
			}
			if (reconnectTimerRef.current) {
				clearTimeout(reconnectTimerRef.current)
			}
		}
	}, [connectClient])

	return {
		publish,
		loading,
		error,
		isConnected,
	}
}
