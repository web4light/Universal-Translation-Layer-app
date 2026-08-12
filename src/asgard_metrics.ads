-- ============================================================
--  Asgard Lab — SPARK Metrics Generator
--  Formálně verifikovaný monitoring
--
--  SPARK generuje metriky → Prometheus sbírá → Grafana zobrazí
--  Žádná metrika nemůže přetéct nebo se ztratit.
--
--  Autor: Pan Jeskyně
--  Verifikace: gnatprove
-- ============================================================

pragma SPARK_Mode (On);

package Asgard_Metrics is

   -- Maximální hodnoty metrik
   Max_Counter : constant := 999_999_999;
   Max_Gauge   : constant := 100_000;

   -- Typy
   subtype Counter_Value is Natural range 0 .. Max_Counter;
   subtype Gauge_Value is Natural range 0 .. Max_Gauge;
   subtype Percent is Natural range 0 .. 100;

   -- Pipeline metriky
   type Pipeline_Metrics is record
      Translations_Total   : Counter_Value := 0;
      Translations_Success : Counter_Value := 0;
      Translations_Failed  : Counter_Value := 0;
      Dubbing_Segments     : Counter_Value := 0;
      Sign_Glosses         : Counter_Value := 0;
      Active_Users         : Gauge_Value := 0;
      Languages_Used       : Gauge_Value := 0;
      Success_Rate         : Percent := 0;
   end record;

   -- Systémové metriky
   type System_Metrics is record
      Uptime_Seconds       : Counter_Value := 0;
      Memory_Used_MB       : Gauge_Value := 0;
      Spark_Checks_Proved  : Counter_Value := 0;
      Spark_Checks_Failed  : Counter_Value := 0;
      Agents_Active        : Gauge_Value := 0;
      Bridges_Connected    : Gauge_Value := 0;
   end record;

   -- Bezpečnostní metriky
   type Security_Metrics is record
      Auth_Success         : Counter_Value := 0;
      Auth_Failed          : Counter_Value := 0;
      Deepfake_Detected    : Counter_Value := 0;
      Mushdo_Passed        : Counter_Value := 0;
      Mushdo_Failed        : Counter_Value := 0;
      Privacy_Purges       : Counter_Value := 0;
   end record;

   -- Celkový stav
   type Asgard_State is record
      Pipeline : Pipeline_Metrics;
      System   : System_Metrics;
      Security : Security_Metrics;
   end record;

   -- =========================================================
   --  Operace
   -- =========================================================

   procedure Initialize (State : out Asgard_State)
     with Post => State.Pipeline.Translations_Total = 0
                  and State.System.Uptime_Seconds = 0
                  and State.Security.Auth_Success = 0;

   -- Zaznamenat překlad
   procedure Record_Translation (State   : in out Asgard_State;
                                 Success : Boolean)
     with Pre => State.Pipeline.Translations_Total < Max_Counter,
          Post => State.Pipeline.Translations_Total =
                  State.Pipeline.Translations_Total'Old + 1;

   -- Zaznamenat dabing
   procedure Record_Dubbing (State    : in out Asgard_State;
                             Segments : Counter_Value)
     with Pre => State.Pipeline.Dubbing_Segments <=
                 Max_Counter - Segments,
          Post => State.Pipeline.Dubbing_Segments =
                  State.Pipeline.Dubbing_Segments'Old + Segments;

   -- Zaznamenat SPARK verifikaci
   procedure Record_Spark_Check (State  : in out Asgard_State;
                                 Proved : Boolean)
     with Pre => State.System.Spark_Checks_Proved < Max_Counter;

   -- Zaznamenat bezpečnostní událost
   procedure Record_Auth (State   : in out Asgard_State;
                          Success : Boolean)
     with Pre => State.Security.Auth_Success < Max_Counter;

   -- Vypočítat success rate
   function Get_Success_Rate (State : Asgard_State) return Percent;

end Asgard_Metrics;
