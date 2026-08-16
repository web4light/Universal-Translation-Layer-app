-- ============================================================
--  Asgard_Orchestrator — Implementace Orchestru
--  Ada/SPARK 2022 — Formálně verifikované jádro systému
--
--  Licence: GNU General Public License v3.0 (GNU GPLv3)
--  Copyright (C) 2026 Pan Jeskyně
--
--  Autor: Pan Jeskyně
--  Standard 700: 12g stříbra = 1 mince
-- ============================================================

pragma SPARK_Mode (On);

package body Asgard_Orchestrator is

   -- ==========================================================
   -- PROBUZENÍ ZÁKLADNY
   -- ==========================================================

   procedure Ignite (O : out Orchestra) is
   begin
      O.State := Operational;

      O.Treasury :=
        (Total_Coins        => 0,
         Total_Silver_Grams => 0.0,
         Is_Full            => True);

      O.Bifrost :=
        (Active_Voice_Count => 0,
         Queued_Segments    => 0,
         Realtime_Ready     => True);

      O.Mesh :=
        (Current_Role      => Standalone,
         Primary_Status    => Healthy,
         Shadow_Status     => Healthy,
         Last_Heartbeat_Ms => 0);

      O.Clans :=
        (Clan_Engineering => (Actions_Today => 0, Active => True),
         Clan_Marketing   => (Actions_Today => 0, Active => True),
         Clan_Operations  => (Actions_Today => 0, Active => True),
         Clan_Legal       => (Actions_Today => 0, Active => True));

      O.Clock_Ms := 0;
   end Ignite;

   -- ==========================================================
   -- ČASOVÝ KROK
   -- ==========================================================

   procedure Tick (O      : in out Orchestra;
                   Now_Ms : Time_Ms) is
   begin
      O.Clock_Ms := Now_Ms;
   end Tick;

   -- ==========================================================
   -- RAŽBA PODLE STANDARDU 700
   -- ==========================================================

   procedure Mint_Coins (O            : in out Orchestra;
                         Silver_Grams : Float;
                         Minted       : out Coin_Count) is
      Coins_To_Mint : Natural;
   begin
      if Silver_Grams < Standard_700_Silver_Grams then
         Minted := 0;
      else
         -- Převod na počet celých mincí po 12g
         if Silver_Grams >= Float (Coin_Count'Last) * Standard_700_Silver_Grams then
            Coins_To_Mint := Coin_Count'Last - O.Treasury.Total_Coins;
         else
            Coins_To_Mint := Natural (Float'Floor (Silver_Grams / Standard_700_Silver_Grams));
         end if;

         -- Garance alespoň 1 mince při vstupu >= 12g
         if Coins_To_Mint = 0 then
            Coins_To_Mint := 1;
         end if;

         -- Ochrana proti přetečení pokladny
         if Coins_To_Mint > Coin_Count'Last - O.Treasury.Total_Coins then
            Coins_To_Mint := Coin_Count'Last - O.Treasury.Total_Coins;
         end if;

         Minted := Coins_To_Mint;
         O.Treasury.Total_Coins := O.Treasury.Total_Coins + Minted;
         O.Treasury.Total_Silver_Grams := O.Treasury.Total_Silver_Grams + Silver_Grams;
         O.Treasury.Is_Full := True;
      end if;
   end Mint_Coins;

   -- ==========================================================
   -- BIFROST DABINGOVÁ FRONTA (Hlasy 1-7)
   -- ==========================================================

   procedure Enqueue_Dubbing (O       : in out Orchestra;
                              Voice   : Voice_ID;
                              Success : out Boolean) is
   begin
      if O.Bifrost.Queued_Segments < Max_Queued_Tasks then
         O.Bifrost.Queued_Segments := O.Bifrost.Queued_Segments + 1;
         if Voice > O.Bifrost.Active_Voice_Count then
            O.Bifrost.Active_Voice_Count := Voice;
         end if;
         Success := True;
      else
         Success := False;
      end if;
   end Enqueue_Dubbing;

   -- ==========================================================
   -- TELEMETRIE A FAILOVER
   -- ==========================================================

   procedure Record_Heartbeat (O         : in out Orchestra;
                               Timestamp : Time_Ms) is
   begin
      O.Mesh.Last_Heartbeat_Ms := Timestamp;
      O.Mesh.Primary_Status := Healthy;
   end Record_Heartbeat;

   procedure Check_And_Trigger_Failover (O : in out Orchestra) is
   begin
      if O.Clock_Ms >= O.Mesh.Last_Heartbeat_Ms + Failover_Timeout_Ms then
         O.State := Failover_Active;
         O.Mesh.Current_Role := Primary_Node;
         O.Mesh.Primary_Status := Unreachable;
      end if;
   end Check_And_Trigger_Failover;

   -- ==========================================================
   -- RADA 4 KLANŮ (Autonomní oddělení)
   -- ==========================================================

   procedure Request_Clan_Action (O       : in out Orchestra;
                                  Clan    : Clan_ID;
                                  Granted : out Boolean) is
   begin
      if O.Clans (Clan).Active
        and then O.Clans (Clan).Actions_Today < Max_Clan_Actions_Daily
      then
         O.Clans (Clan).Actions_Today := O.Clans (Clan).Actions_Today + 1;
         Granted := True;
      else
         Granted := False;
      end if;
   end Request_Clan_Action;

end Asgard_Orchestrator;
