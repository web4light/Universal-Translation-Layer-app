-- ============================================================
--  Asgard Lab — Prometheus Metrics Exporter
--  Ada/SPARK HTTP server co servíruje /metrics pro Prometheus
--
--  Běží na portu 9306 a exportuje stav celého systému.
--  SPARK garantuje že metriky nikdy nepřetečou.
--
--  Autor: Pan Jeskyně
--  Verifikace: gnatprove
-- ============================================================

pragma SPARK_Mode (On);

package Prometheus_Exporter is

   -- Port pro metrics endpoint
   Metrics_Port : constant := 9_307;

   -- Maximální délka metrics výstupu
   Max_Output_Length : constant := 8_192;
   subtype Output_Length is Natural range 0 .. Max_Output_Length;

   -- Formát jedné metriky: "nazev{label} hodnota\n"
   Max_Metric_Name : constant := 64;
   Max_Label       : constant := 128;

   subtype Metric_Name_Len is Natural range 0 .. Max_Metric_Name;
   subtype Label_Len is Natural range 0 .. Max_Label;

   -- Stav služeb (jistič: nahoru/dolu)
   type Service_State is (Up, Down);

   -- Služby co monitorujeme
   type Service_ID is (Shadow_Node, Watchdog, Privacy_423,
                       Asgard_API, Cave_Lab, Faucet_DNS,
                       Prometheus_Self, Grafana);

   -- Stav všech služeb
   type Service_States is array (Service_ID) of Service_State;

   -- Celkový snapshot pro export
   type Metrics_Snapshot is record
      Services           : Service_States := (others => Down);
      Translations_Total : Natural range 0 .. 999_999_999 := 0;
      Dubbing_Segments   : Natural range 0 .. 999_999_999 := 0;
      Sign_Glosses       : Natural range 0 .. 999_999_999 := 0;
      Spark_Proved       : Natural range 0 .. 999_999 := 0;
      Uptime_Seconds     : Natural range 0 .. 999_999_999 := 0;
      Active_Users       : Natural range 0 .. 999_999 := 0;
   end record;

   -- =========================================================
   --  Operace
   -- =========================================================

   -- Nastav stav služby (jistič nahoru/dolu)
   procedure Set_Service (Snapshot : in out Metrics_Snapshot;
                          Service  : Service_ID;
                          State    : Service_State)
     with Post => Snapshot.Services (Service) = State;

   -- Zjisti stav služby
   function Get_Service (Snapshot : Metrics_Snapshot;
                         Service  : Service_ID) return Service_State;

   -- Všechny jističe nahoře?
   function All_Up (Snapshot : Metrics_Snapshot) return Boolean;

   -- Počet služeb nahoře
   function Count_Up (Snapshot : Metrics_Snapshot) return Natural
     with Post => Count_Up'Result <= Service_ID'Pos (Service_ID'Last) + 1;

end Prometheus_Exporter;
