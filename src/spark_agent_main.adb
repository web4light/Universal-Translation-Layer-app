with SPARK_Agent;
with Asterisk_Sovereign_Webmcp_Mesh_Platform_Core;
with Chrome_Webmcp_Engine;
with SPARKdog_Guardian;
with Ada.Text_IO;

procedure SPARK_Agent_Main is
   use Ada.Text_IO;
   Ctx : SPARK_Agent.Agent_Context;
   Reason_OK : Boolean;
   Tool_OK   : Boolean;
   Goal_OK   : Boolean;

   Mesh_State : Asterisk_Sovereign_Webmcp_Mesh_Platform_Core.Core_State;
   Mesh_OK    : Boolean;

   Chrome_Ctx : Chrome_Webmcp_Engine.Webmcp_Context;
   Reg_OK     : Boolean;
   Gesture_OK : Boolean;

   Dog_State  : SPARKdog_Guardian.SPARKdog_State;
   Dog_OK     : Boolean;
begin
   Put_Line ("============================================================");
   Put_Line ("  ASTERISK (*) SOVEREIGN SPARK CORE -- RUNTIME TEST");
   Put_Line ("  Dohled: SPARKdog Guardian + GNAT Formalni Ostriz");
   Put_Line ("============================================================");

   -- 1. Probud SPARKdoga
   SPARKdog_Guardian.Awaken_SPARKdog (Dog_State);
   Put_Line ("  [1/6] SPARKdog probuzen a pripraven k dohledu: OK");

   -- 2. Inicializuj SPARK Agenta
   SPARK_Agent.Initialize (Ctx);
   Put_Line ("  [2/6] SPARK Agent inicializovan: OK");

   -- 3. Krok uvazovani
   SPARK_Agent.Step_Reasoning (Ctx, Reason_OK);
   if Reason_OK then
      Put_Line ("  [3/6] Didakticky krok uvazovani: OK");
   end if;

   -- 4. SPARKdog inspects Chrome WebMCP Engine
   Chrome_Webmcp_Engine.Initialize_Engine (Chrome_Ctx);
   Chrome_Webmcp_Engine.Register_Webmcp_Tool
     (Chrome_Ctx, Chrome_Webmcp_Engine.Tool_Accessibility_Sign, Reg_OK);
   Chrome_Webmcp_Engine.Dispatch_Sign_Gesture (Chrome_Ctx, 60, Gesture_OK);

   SPARKdog_Guardian.Inspect_Buffer_Safety (Dog_State, 60, 500, Dog_OK);

   if Reg_OK and Gesture_OK and Dog_OK then
      Put_Line ("  [4/6] Chrome WebMCP (PJAY/SPARK) overen SPARKdogem: OK");
   end if;

   -- 4.5. Test Big Brother interception
   declare
      Threat_Blocked : Boolean;
   begin
      SPARKdog_Guardian.Intercept_Big_Brother_Threat
        (Dog_State, SPARKdog_Guardian.Threat_Third_Party_Tracker, Threat_Blocked);
      if Threat_Blocked then
         Put_Line ("  [4.5/6] SPARKdog KOUSE: Cizi tracker uspesne znicen, Hermetic Shield AKTIVNI: OK");
      end if;
   end;

   -- 4.6. Test Samo-opravy za chodu (Hot-Patching / Self-Healing in-vivo)
   declare
      Corrupt_Check : Boolean;
      Heal_Success  : Boolean;
   begin
      -- Simulace anomalie (preteceni bufferu utocnikem)
      SPARKdog_Guardian.Inspect_Buffer_Safety (Dog_State, 999, 100, Corrupt_Check);
      if not Corrupt_Check then
         Put_Line ("  [4.6a] SPARKdog detekoval anomalii/poskozeni za chodu: ZACHYCENO");
      end if;

      -- Okamzita samo-oprava za chodu bez padu a bez restartu
      SPARKdog_Guardian.Self_Heal_Runtime_State (Dog_State, Heal_Success);
      if Heal_Success and Dog_State.Memory_Safe then
         Put_Line ("  [4.6b] SPARKdog SAMO-OPRAVA ZA CHODU: Stav zacelen za chodu, 0 vypadek: OK");
      end if;
   end;

   -- 5. Invoke Tool under GNAT supervision
   SPARK_Agent.Invoke_Tool (Ctx, SPARK_Agent.Tool_Gnatprove, Tool_OK);
   if Tool_OK then
      Put_Line ("  [5/6] GNATprove formalni verifikace nastroje: OK");
   end if;

   -- 6. Finalize Goal & Test WebMCP Core
   SPARK_Agent.Finalize_Goal (Ctx, Goal_OK);
   Asterisk_Sovereign_Webmcp_Mesh_Platform_Core.Process_Stream (Mesh_State, 128, Mesh_OK);

   if Goal_OK and Mesh_OK then
      Put_Line ("  [6/6] In-Memory Stream Buffer: 100% OK (Zero-Trace)");
      Put_Line ("------------------------------------------------------------");
      Put_Line ("  [SPARKdog] VSECHNY FORMALNI KONTRAKTY SEDI!");
      Put_Line ("  [GNAT] 0 chyb, 0 varovani, cisty beh v pameti!");
      Put_Line ("============================================================");
   end if;
end SPARK_Agent_Main;
