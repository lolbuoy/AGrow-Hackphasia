import { Route, Switch } from "wouter"
import Home from "./pages/Home"
import Zone from "./pages/Zone"
import Fetching from "./pages/Fetching"
import Plan from "./pages/Plan"
import Recommendations from "./pages/Recommendations"

function App() {
	return (
		<div className="flex flex-col justify-stretch items-stretch h-screen w-screen bg">
			<header className="shadow-md px-8 py-8 text-center bg-white/90">
				<h4 className="font-bold text-2xl text-green-800 tracking-tighter">AGrow</h4>
			</header>
			<main className="p-12 overflow-y-auto h-full">
				<Switch>
					<Route path="/" component={Home} />
					<Route path="/zone" component={Zone} />
					<Route path="/fetching" component={Fetching} />
					<Route path="/recommendations" component={Recommendations} />
					<Route path="/plan/:crop">{(params) => <Plan crop={params.crop} />}</Route>

					{/* <Route path="/content/:id">{(params) => <Content id={params.id} />}</Route> */}

					<Route>404: No such page!</Route>
				</Switch>
			</main>
		</div>
	)
}

export default App
