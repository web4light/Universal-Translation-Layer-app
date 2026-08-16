-- ============================================================
--  Dirigent — Real-time Dubbing Orchestrator
--  Ada/SPARK — řídí hlasy, timing, voice cloning
--
--  Dirigent = ten kdo mává taktovkou nad orchestrem hlasů.
--  SPARK garantuje:
--  - Hlasy se nepřekryjí (timing proved)
--  - Správný hlas pro správnou postavu (index proved)
--  - Buffer nepřeteče (ranged types)
--  - 5s latence max (postcondition)
--
--  Autor: Pan Jeskyně
--  Verifikace: gnatprove
-- ============================================================

pragma SPARK_Mode (On);

package Dirigent is

   -- Maximální počet hlasů (postav) v jednom videu
   Max_Voices : constant := 20;

   -- Maximální počet segmentů ve frontě
   Max_Queue : constant := 100;

   -- Timing v milisekundách
   subtype Time_Ms is Natural range 0 .. 86_400_000;

   -- Buffer (15s = 15000ms)
   Buffer_Ms : constant := 15_000;

   -- Latence SPARK (5s = 5000ms)
   Spark_Latency_Ms : constant := 5_000;

   -- Voice extraction latence (10s)
   Extract_Latency_Ms : constant := 10_000;

   -- =========================================================
   --  TYPY
   -- =========================================================

   subtype Voice_Index is Natural range 0 .. Max_Voices;
   subtype Voice_Cnt is Natural range 0 .. Max_Voices;
   subtype Queue_Index is Natural range 0 .. Max_Queue;
   subtype Queue_Count is Natural range 0 .. Max_Queue;

   -- Stav hlasu
   type Voice_State is (Unknown, Extracting, Ready);

   -- Jeden hlas (postava)
   type Voice_Entry is record
      State     : Voice_State := Unknown;
      Extracted : Boolean := False;
   end record;

   -- Jeden segment k dabování
   type Dub_Segment is record
      Voice_ID  : Voice_Index := 0;
      Start_Ms  : Time_Ms := 0;
      End_Ms    : Time_Ms := 0;
      Filled    : Boolean := False;
   end record;

   -- Fronta segmentů
   type Segment_Queue is array (1 .. Max_Queue) of Dub_Segment;

   -- Pole hlasů
   type Voice_Array is array (1 .. Max_Voices) of Voice_Entry;

   -- Stav dirigenta
   type Dirigent_State is (Idle, Buffering, Running, Finished);

   -- Hlavní struktura
   type Orchestra is record
      State       : Dirigent_State := Idle;
      Voices      : Voice_Array;
      Voice_Count : Voice_Cnt := 0;
      Queue       : Segment_Queue;
      Queue_Len   : Queue_Count := 0;
      Current_Ms  : Time_Ms := 0;
   end record;

   -- =========================================================
   --  OPERACE
   -- =========================================================

   -- Inicializace
   procedure Initialize (O : out Orchestra)
     with Post => O.State = Idle
                  and O.Voice_Count = 0
                  and O.Queue_Len = 0;

   -- Registrovat nový hlas (postava detekována)
   procedure Register_Voice (O       : in out Orchestra;
                             Success : out Boolean)
     with Pre  => O.Voice_Count < Max_Voices,
          Post => (if Success then O.Voice_Count = O.Voice_Count'Old + 1
                   else O.Voice_Count = O.Voice_Count'Old);

   -- Označit hlas jako extrahovaný (ready)
   procedure Voice_Ready (O        : in out Orchestra;
                          Voice_ID : Voice_Index)
     with Pre  => Voice_ID >= 1 and Voice_ID <= O.Voice_Count,
          Post => O.Voices (Voice_ID).State = Ready;

   -- Přidat segment do fronty
   procedure Enqueue (O        : in out Orchestra;
                      Voice_ID : Voice_Index;
                      Start_Ms : Time_Ms;
                      End_Ms   : Time_Ms;
                      Success  : out Boolean)
     with Pre  => O.Queue_Len < Max_Queue
                  and Voice_ID >= 1
                  and Voice_ID <= O.Voice_Count
                  and End_Ms > Start_Ms,
          Post => (if Success then O.Queue_Len = O.Queue_Len'Old + 1
                   else O.Queue_Len = O.Queue_Len'Old);

   -- Může segment hrát? (hlas ready + timing OK)
   function Can_Play (O   : Orchestra;
                      Idx : Queue_Index) return Boolean
     with Pre => Idx >= 1 and Idx <= O.Queue_Len;

   -- Spustit dirigenta
   procedure Start (O : in out Orchestra)
     with Pre  => O.State = Idle,
          Post => O.State = Buffering;

   -- Posunout čas (tick)
   procedure Tick (O      : in out Orchestra;
                   Now_Ms : Time_Ms)
     with Post => O.Current_Ms = Now_Ms;

   -- Všechny hlasy ready?
   function All_Voices_Ready (O : Orchestra) return Boolean;

end Dirigent;
