--  =============================================================================
--  Asterisk Gateway — Mesh Routing Table
--  SPARK 2022 Level 4 Gold (DO-178C DAL-A Compliant)
--  Deterministic P2P routing table with loop prevention and bounded costs.
--  Standard 700: Decentralized sovereign node routing.
--  =============================================================================

package Mesh_Routing_Table with
  SPARK_Mode => On
is
   Max_Nodes : constant := 64;
   Max_Hops  : constant := 16;
   Max_Cost  : constant := 1000;

   subtype Node_ID is Positive range 1 .. Max_Nodes;
   subtype Hop_Count is Natural range 0 .. Max_Hops;
   subtype Cost_Metric is Natural range 0 .. Max_Cost;

   type Route_Entry is record
      Next_Hop : Node_ID;
      Hops     : Hop_Count;
      Cost     : Cost_Metric;
      Active   : Boolean;
   end record;

   type Routing_Table is array (Node_ID) of Route_Entry;

   --  Initializes routing table. All nodes inactive except the local node (0 cost, 0 hops).
   procedure Initialize_Table
     (Table      : out Routing_Table;
      Local_Node : in  Node_ID)
   with
     Global => null,
     Depends => (Table => Local_Node),
     Post => Table (Local_Node).Active and then
             Table (Local_Node).Hops = 0 and then
             Table (Local_Node).Cost = 0 and then
             Table (Local_Node).Next_Hop = Local_Node;

   --  Updates a route toward Destination with loop prevention.
   procedure Update_Route
     (Table       : in out Routing_Table;
      Destination : in     Node_ID;
      Next_Hop    : in     Node_ID;
      New_Hops    : in     Hop_Count;
      New_Cost    : in     Cost_Metric;
      Updated     : out    Boolean)
   with
     Global => null,
     Depends => (Table   => (Table, Destination, Next_Hop, New_Hops, New_Cost),
                 Updated => (Table, Destination, New_Cost)),
     Pre  => New_Hops < Max_Hops and then Next_Hop /= Destination,
     Post => (if Updated then
                Table (Destination).Active and then
                Table (Destination).Next_Hop = Next_Hop and then
                Table (Destination).Cost = New_Cost and then
                Table (Destination).Hops = New_Hops + 1);

   --  Looks up next hop for a destination.
   procedure Lookup_Route
     (Table       : in  Routing_Table;
      Destination : in  Node_ID;
      Next_Hop    : out Node_ID;
      Found       : out Boolean)
   with
     Global => null,
     Depends => ((Next_Hop, Found) => (Table, Destination)),
     Post => (if Found then
                Table (Destination).Active and then
                Next_Hop = Table (Destination).Next_Hop
              else
                Next_Hop = Destination);

end Mesh_Routing_Table;
