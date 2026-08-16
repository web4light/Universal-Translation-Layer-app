-- ============================================================
--  Agent Přemysl — Vrchní Správce a Oráč Sítě (Mesh Orchestrator)
--  Ada/SPARK 2022 — Formálně verifikovaný síťový orchestrátor
--
--  Licence: GNU General Public License v3.0 (GNU GPLv3)
--  Copyright (C) 2026 Pan Jeskyně
--
--  Inspirován Přemyslem Oráčem — zakladatelem pevné půdy a řádu:
--  Orá síťové brázdy (SDN trasy), sází uzly (Peer Discovery),
--  sklízí telemetrii (Heartbeaty) a vyvažuje zátěž decentralizované sítě.
--
--  Autor: Pan Jeskyně
--  Standard: 700 / Protokol 4.23
-- ============================================================

pragma SPARK_Mode (On);

package Agent_Premysl is

   -- ==========================================================
   -- KONSTANTY
   -- ==========================================================

   Max_Mesh_Nodes : constant := 100;
   Heartbeat_Limit_Ms : constant := 15_000;

   -- ==========================================================
   -- TYPY A ROZSAHY
   -- ==========================================================

   subtype Node_Index is Natural range 0 .. Max_Mesh_Nodes;
   subtype Node_Count is Natural range 0 .. Max_Mesh_Nodes;
   subtype Latency_Ms is Natural range 0 .. 10_000;

   type Node_Role is (Primary_Worker, Shadow_Guardian, Peer_Relay);
   type Node_Status is (Active, Syncing, Offline);

   -- Záznam o jednom uzlu sítě (brázdě)
   type Mesh_Node is record
      ID          : Node_Index  := 0;
      Role        : Node_Role   := Peer_Relay;
      Status      : Node_Status := Offline;
      Latency     : Latency_Ms  := 0;
      Load_Pct    : Natural range 0 .. 100 := 0;
   end record;

   type Node_Array is array (1 .. Max_Mesh_Nodes) of Mesh_Node;

   -- Celkový stav orané sítě pod Přemyslem
   type Premysl_Mesh_State is record
      Nodes        : Node_Array;
      Active_Nodes : Node_Count := 0;
      Primary_ID   : Node_Index := 0;
      Shadow_ID    : Node_Index := 0;
      Total_Ploughed_Packets : Natural := 0;
   end record;

   -- ==========================================================
   -- KONTRAKTY A OPERACE
   -- ==========================================================

   -- Inicializace sítě a oráče Přemysla
   procedure Initialize (P : out Premysl_Mesh_State)
     with Post => P.Active_Nodes = 0
                  and P.Primary_ID = 0
                  and P.Shadow_ID = 0;

   -- Zaorání (připojení) nového uzlu do sítě
   procedure Plough_Node (P       : in out Premysl_Mesh_State;
                          Role    : Node_Role;
                          Success : out Boolean)
     with Pre  => P.Active_Nodes < Max_Mesh_Nodes,
          Post => (if Success then P.Active_Nodes = P.Active_Nodes'Old + 1
                   else P.Active_Nodes = P.Active_Nodes'Old);

   -- Sklizeň telemetrie a vyvážení zátěže
   procedure Harvest_Telemetry (P       : in out Premysl_Mesh_State;
                                Node_ID : Node_Index;
                                Latency : Latency_Ms;
                                Load    : Natural)
     with Pre => Node_ID >= 1 and Node_ID <= P.Active_Nodes and Load <= 100,
          Post => P.Nodes (Node_ID).Latency = Latency
                  and P.Nodes (Node_ID).Load_Pct = Load;

end Agent_Premysl;
