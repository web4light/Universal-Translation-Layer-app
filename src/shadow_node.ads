-- ============================================================
--  Shadow Node — Stínovací uzel pro Vakuovou Mincovnu
--  Poskytuje redundanci a high availability
--
--  Autor: Pan Jeskyně
--  Asistent: Kiro (Claude)
--  Standard 700: 12g stříbra
--  Verifikace: SPARK
-- ============================================================
pragma SPARK_Mode (Off);  -- GNAT.Sockets není SPARK kompatibilní

with Prometheus_Exporter; use Prometheus_Exporter;

package Shadow_Node is

   -- Konfigurace
   Shadow_Port      : constant := 9303;
   Primary_Port     : constant := 9302;
   Heartbeat_Sec    : constant := 5;
   Failover_Timeout : constant := 15;

   -- Stav Shadow Node
   type Node_Mode is (Shadow, Primary);

   type Shadow_State is record
      Mode               : Node_Mode := Shadow;
      Synced_Coins       : Natural   := 0;
      Synced_Silver_Mg   : Natural   := 0;  -- v miligramech (12000 = 12g)
      Sync_Errors        : Natural   := 0;
      Cycle              : Natural   := 0;
      Is_Primary_Alive   : Boolean   := True;
      Metrics            : Metrics_Snapshot;
   end record;

   -- Hlavní vstupní bod
   procedure Run;

private

   -- HTTP GET na /metrics Primary Node
   function Check_Primary_Health (State : in out Shadow_State) return Boolean;

   -- Synchronizace stavu z Primary
   procedure Sync_From_Primary (State : in out Shadow_State);

   -- Prometheus výstup na portu 9303

   -- Přechod na Primary mód (failover)
   procedure Become_Primary (State : in out Shadow_State);

   -- Vrácení do Shadow módu
   procedure Demote_To_Shadow (State : in out Shadow_State);

   -- Log s timestampem
   procedure Log (Prefix : String; Msg : String);

end Shadow_Node;
