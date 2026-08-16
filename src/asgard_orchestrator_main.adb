-- ============================================================
--  Asgard_Orchestrator_Main — Hlavní CLI binárka Orchestru
--  Výstup: JSON pro asgard_server.py a webový Mission Control
--
--  Autor: Pan Jeskyně
-- ============================================================

pragma SPARK_Mode (Off);

with Ada.Text_IO;         use Ada.Text_IO;
with Ada.Command_Line;
with Ada.Strings.Fixed;
with Asgard_Orchestrator; use Asgard_Orchestrator;

procedure Asgard_Orchestrator_Main is

   function Img (N : Natural) return String is
      Raw : constant String := Natural'Image (N);
   begin
      return Ada.Strings.Fixed.Trim (Raw, Ada.Strings.Left);
   end Img;

   function Flt_Img (F : Float) return String is
      Raw : constant String := Float'Image (F);
   begin
      return Ada.Strings.Fixed.Trim (Raw, Ada.Strings.Left);
   end Flt_Img;

   O       : Orchestra;
   Minted  : Coin_Count;
   Success : Boolean;
   Granted : Boolean;

begin
   -- 1. Probuzení základny
   Ignite (O);

   -- 2. Simulace ražby (120g stříbra = 10 Grošů)
   Mint_Coins (O, 120.0, Minted);

   -- 3. Zařazení 3 dabingových hlasů
   Enqueue_Dubbing (O, 1, Success);
   Enqueue_Dubbing (O, 2, Success);
   Enqueue_Dubbing (O, 3, Success);

   -- 4. Záznam heartbeatu
   Record_Heartbeat (O, 1_000);
   Tick (O, 2_000);

   -- 5. Požadavek akce klanu Engineering
   Request_Clan_Action (O, Clan_Engineering, Granted);

   -- 6. Výstup strukturovaného JSONu na stdout
   Put_Line ("{");
   Put_Line ("  ""status"": ""operational"",");
   Put_Line ("  ""standard"": 700,");
   Put_Line ("  ""treasury"": {");
   Put_Line ("    ""total_coins"": " & Img (O.Treasury.Total_Coins) & ",");
   Put_Line ("    ""silver_grams"": " & Flt_Img (O.Treasury.Total_Silver_Grams) & ",");
   Put_Line ("    ""is_full"": true");
   Put_Line ("  },");
   Put_Line ("  ""bifrost"": {");
   Put_Line ("    ""active_voices"": " & Img (O.Bifrost.Active_Voice_Count) & ",");
   Put_Line ("    ""queued_segments"": " & Img (O.Bifrost.Queued_Segments) & ",");
   Put_Line ("    ""realtime_ready"": true");
   Put_Line ("  },");
   Put_Line ("  ""mesh"": {");
   Put_Line ("    ""primary_status"": ""healthy"",");
   Put_Line ("    ""shadow_status"": ""healthy"",");
   Put_Line ("    ""last_heartbeat_ms"": " & Img (O.Mesh.Last_Heartbeat_Ms));
   Put_Line ("  },");
   Put_Line ("  ""clans"": {");
   Put_Line ("    ""engineering_actions"": " & Img (O.Clans (Clan_Engineering).Actions_Today));
   Put_Line ("  }");
   Put_Line ("}");

end Asgard_Orchestrator_Main;
