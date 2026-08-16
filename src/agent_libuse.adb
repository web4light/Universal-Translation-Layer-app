-- ============================================================
--  Kněžna Libuše — Implementace Věštkyně Sítě (Prometheus & Geth)
--  Ada/SPARK 2022 — Formálně verifikované orakulum
--
--  Licence: GNU General Public License v3.0 (GNU GPLv3)
--  Copyright (C) 2026 Pan Jeskyně
--
--  Autor: Pan Jeskyně
-- ============================================================

pragma SPARK_Mode (On);

package body Agent_Libuse is

   -- ==========================================================
   -- INICIALIZACE
   -- ==========================================================

   procedure Initialize (L : out Libuse_Oracle) is
   begin
      L.Prometheus_Port := 9302;
      L.Geth_Block      := 0;
      L.CPU_Pressure    := 0;
      L.RAM_Pressure    := 0;
      L.Health          := Serene_Golden;
      L.Geth_Sync_OK    := True;
   end Initialize;

   -- ==========================================================
   -- KONTROLA TELEMETRIE
   -- ==========================================================

   procedure Scrutinize_Metrics (L            : in out Libuse_Oracle;
                                 CPU_Usage    : Metric_Gauge;
                                 RAM_Usage    : Metric_Gauge;
                                 Current_Blk  : Block_Number) is
   begin
      L.CPU_Pressure := CPU_Usage;
      L.RAM_Pressure := RAM_Usage;
      L.Geth_Block   := Current_Blk;

      if CPU_Usage > 90 or RAM_Usage > 90 then
         L.Health := Eclipse_Critical;
      elsif CPU_Usage > 75 or RAM_Usage > 75 then
         L.Health := Clouded_Warning;
      else
         L.Health := Serene_Golden;
      end if;
   end Scrutinize_Metrics;

   -- ==========================================================
   -- OVĚŘENÍ GETH ZRCADLA
   -- ==========================================================

   function Is_Geth_Mirror_Pure (L : Libuse_Oracle) return Boolean is
   begin
      return L.Geth_Sync_OK and then L.Health /= Eclipse_Critical;
   end Is_Geth_Mirror_Pure;

end Agent_Libuse;
