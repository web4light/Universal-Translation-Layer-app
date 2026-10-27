--  =============================================================================
--  Asterisk Gateway — Mesh Routing Table Implementation
--  SPARK 2022 Level 4 Gold (DO-178C DAL-A Compliant)
--  =============================================================================

package body Mesh_Routing_Table with
  SPARK_Mode => On
is

   procedure Initialize_Table
     (Table      : out Routing_Table;
      Local_Node : in  Node_ID)
   is
   begin
      Table := (others => (Next_Hop => 1,
                           Hops     => Max_Hops,
                           Cost     => Max_Cost,
                           Active   => False));
      Table (Local_Node) := (Next_Hop => Local_Node,
                             Hops     => 0,
                             Cost     => 0,
                             Active   => True);
   end Initialize_Table;

   procedure Update_Route
     (Table       : in out Routing_Table;
      Destination : in     Node_ID;
      Next_Hop    : in     Node_ID;
      New_Hops    : in     Hop_Count;
      New_Cost    : in     Cost_Metric;
      Updated     : out    Boolean)
   is
   begin
      if not Table (Destination).Active
        or else New_Cost < Table (Destination).Cost
      then
         Table (Destination) := (Next_Hop => Next_Hop,
                                 Hops     => New_Hops + 1,
                                 Cost     => New_Cost,
                                 Active   => True);
         Updated := True;
      else
         Updated := False;
      end if;
   end Update_Route;

   procedure Lookup_Route
     (Table       : in  Routing_Table;
      Destination : in  Node_ID;
      Next_Hop    : out Node_ID;
      Found       : out Boolean)
   is
   begin
      if Table (Destination).Active then
         Next_Hop := Table (Destination).Next_Hop;
         Found    := True;
      else
         Next_Hop := Destination;
         Found    := False;
      end if;
   end Lookup_Route;

end Mesh_Routing_Table;
