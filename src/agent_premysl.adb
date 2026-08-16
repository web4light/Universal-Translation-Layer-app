-- ============================================================
--  Agent Přemysl — Implementace Správce Sítě (Mesh Orchestrator)
--  Ada/SPARK 2022 — Formálně verifikované jádro sítě
--
--  Licence: GNU General Public License v3.0 (GNU GPLv3)
--  Copyright (C) 2026 Pan Jeskyně
--
--  Autor: Pan Jeskyně
-- ============================================================

pragma SPARK_Mode (On);

package body Agent_Premysl is

   -- ==========================================================
   -- INICIALIZACE
   -- ==========================================================

   procedure Initialize (P : out Premysl_Mesh_State) is
   begin
      P.Active_Nodes := 0;
      P.Primary_ID   := 0;
      P.Shadow_ID    := 0;
      P.Total_Ploughed_Packets := 0;

      for I in 1 .. Max_Mesh_Nodes loop
         P.Nodes (I) := (ID       => 0,
                         Role     => Peer_Relay,
                         Status   => Offline,
                         Latency  => 0,
                         Load_Pct => 0);
      end loop;
   end Initialize;

   -- ==========================================================
   -- ZAORÁNÍ UZLU
   -- ==========================================================

   procedure Plough_Node (P       : in out Premysl_Mesh_State;
                          Role    : Node_Role;
                          Success : out Boolean) is
   begin
      if P.Active_Nodes < Max_Mesh_Nodes then
         P.Active_Nodes := P.Active_Nodes + 1;
         P.Nodes (P.Active_Nodes) := (ID       => P.Active_Nodes,
                                      Role     => Role,
                                      Status   => Active,
                                      Latency  => 5,
                                      Load_Pct => 10);

         if Role = Primary_Worker and P.Primary_ID = 0 then
            P.Primary_ID := P.Active_Nodes;
         elsif Role = Shadow_Guardian and P.Shadow_ID = 0 then
            P.Shadow_ID := P.Active_Nodes;
         end if;

         Success := True;
      else
         Success := False;
      end if;
   end Plough_Node;

   -- ==========================================================
   -- SKLIZEŇ TELEMETRIE
   -- ==========================================================

   procedure Harvest_Telemetry (P       : in out Premysl_Mesh_State;
                                Node_ID : Node_Index;
                                Latency : Latency_Ms;
                                Load    : Natural) is
   begin
      if Node_ID >= 1 and then Node_ID <= P.Active_Nodes then
         P.Nodes (Node_ID).Latency := Latency;
         if Load <= 100 then
            P.Nodes (Node_ID).Load_Pct := Load;
         else
            P.Nodes (Node_ID).Load_Pct := 100;
         end if;
         P.Total_Ploughed_Packets := P.Total_Ploughed_Packets + 1;
      end if;
   end Harvest_Telemetry;

end Agent_Premysl;
