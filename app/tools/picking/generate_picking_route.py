"""Generate picking route tool"""

from typing import Dict, Any, List
from pydantic import BaseModel, Field
from app.tools.base import BaseTool, ToolResult
from app.clients.database_client import DatabaseClient
from app.utils.validators import validate_order_id
from app.utils.error_handlers import handle_tool_error


class GeneratePickingRouteInput(BaseModel):
    """Input schema for generate_picking_route"""
    order_id: str = Field(..., description="Order ID")


class GeneratePickingRoute(BaseTool):
    """Generate optimized picking route using TSP algorithm"""
    
    name = "generate_picking_route"
    description = "Optimize picking route to minimize travel distance in warehouse using TSP algorithm"
    
    def __init__(self, config):
        super().__init__(config)
        self.db = DatabaseClient(config)
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Get input schema"""
        return {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "Order ID"
                }
            },
            "required": ["order_id"]
        }
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool"""
        try:
            # Parse input
            input_data = GeneratePickingRouteInput(**kwargs)
            
            # Validate input
            validate_order_id(input_data.order_id)
            
            # Connect to database
            await self.db.connect()
            
            # Get order items with locations
            query = """
                SELECT 
                    oi.sku_code,
                    oi.quantity,
                    s.location_code,
                    l.zone_id,
                    l.row_id,
                    l.shelf_id,
                    l.x_coordinate,
                    l.y_coordinate,
                    l.z_coordinate
                FROM order_items oi
                JOIN inventory_stock s ON oi.sku_code = s.sku_code
                JOIN warehouse_locations l ON s.location_code = l.location_code
                WHERE oi.order_id = $1
                AND s.available_qty >= oi.quantity
                ORDER BY l.zone_id, l.row_id, l.shelf_id
            """
            
            items_with_locations = await self.db.fetch_many(query, input_data.order_id)
            
            # Close connection
            await self.db.disconnect()
            
            if not items_with_locations:
                return ToolResult(
                    success=False,
                    error=f"No items with available stock found for order: {input_data.order_id}",
                    error_code="NOT_FOUND"
                )
            
            # Get unique locations
            unique_locations = self._get_unique_locations(items_with_locations)
            
            # Generate optimized route using TSP
            optimized_route = self._solve_tsp(unique_locations)
            
            # Calculate route metrics
            route_metrics = self._calculate_route_metrics(optimized_route)
            
            return ToolResult(
                success=True,
                data={
                    "order_id": input_data.order_id,
                    "total_items": len(items_with_locations),
                    "unique_locations": len(unique_locations),
                    "optimized_route": optimized_route,
                    "route_metrics": route_metrics,
                    "picking_instructions": self._generate_picking_instructions(optimized_route, items_with_locations)
                }
            )
            
        except Exception as e:
            return handle_tool_error(e, self.name)
    
    def _get_unique_locations(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get unique locations from items"""
        seen = set()
        unique_locations = []
        
        for item in items:
            location_code = item.get('location_code')
            if location_code and location_code not in seen:
                seen.add(location_code)
                unique_locations.append({
                    "location_code": location_code,
                    "zone_id": item.get('zone_id'),
                    "row_id": item.get('row_id'),
                    "shelf_id": item.get('shelf_id'),
                    "x": item.get('x_coordinate', 0),
                    "y": item.get('y_coordinate', 0),
                    "z": item.get('z_coordinate', 0)
                })
        
        return unique_locations
    
    def _solve_tsp(self, locations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Solve Traveling Salesperson Problem for route optimization"""
        if not locations:
            return []
        
        if len(locations) <= 2:
            return locations
        
        # Simple nearest neighbor algorithm (can be upgraded to more sophisticated TSP)
        unvisited = locations.copy()
        route = [unvisited.pop(0)]  # Start from first location
        
        while unvisited:
            current = route[-1]
            nearest = min(
                unvisited,
                key=lambda loc: self._calculate_distance(current, loc)
            )
            route.append(nearest)
            unvisited.remove(nearest)
        
        return route
    
    def _calculate_distance(self, loc1: Dict[str, Any], loc2: Dict[str, Any]) -> float:
        """Calculate Euclidean distance between two locations"""
        x1, y1, z1 = loc1.get('x', 0), loc1.get('y', 0), loc1.get('z', 0)
        x2, y2, z2 = loc2.get('x', 0), loc2.get('y', 0), loc2.get('z', 0)
        
        return ((x2 - x1)**2 + (y2 - y1)**2 + (z2 - z1)**2)**0.5
    
    def _calculate_route_metrics(self, route: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate route metrics"""
        if len(route) < 2:
            return {
                "total_distance_m": 0,
                "estimated_time_seconds": 0,
                "location_count": len(route)
            }
        
        total_distance = 0
        for i in range(len(route) - 1):
            total_distance += self._calculate_distance(route[i], route[i + 1])
        
        # Estimate time (assuming 1 meter per second walking speed)
        estimated_time = total_distance * 1.0  # 1 second per meter
        
        return {
            "total_distance_m": round(total_distance, 2),
            "estimated_time_seconds": round(estimated_time, 2),
            "estimated_time_minutes": round(estimated_time / 60, 2),
            "location_count": len(route)
        }
    
    def _generate_picking_instructions(
        self, 
        route: List[Dict[str, Any]], 
        items: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate detailed picking instructions"""
        instructions = []
        
        # Create location to items mapping
        location_items = {}
        for item in items:
            loc_code = item.get('location_code')
            if loc_code not in location_items:
                location_items[loc_code] = []
            location_items[loc_code].append(item)
        
        # Generate instructions for each stop
        for i, location in enumerate(route):
            loc_code = location.get('location_code')
            items_at_location = location_items.get(loc_code, [])
            
            instructions.append({
                "stop_number": i + 1,
                "location_code": loc_code,
                "zone": location.get('zone_id'),
                "row": location.get('row_id'),
                "shelf": location.get('shelf_id'),
                "items_to_pick": [
                    {
                        "sku_code": item.get('sku_code'),
                        "quantity": item.get('quantity')
                    }
                    for item in items_at_location
                ],
                "total_items_at_stop": len(items_at_location),
                "instruction": f"Go to {loc_code} and pick {len(items_at_location)} item(s)"
            })
        
        return instructions
