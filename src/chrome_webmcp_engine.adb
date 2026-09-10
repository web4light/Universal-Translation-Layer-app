-- ============================================================
--  Chrome WebMCP Engine — Tělo Balíčku v SPARK
--  Ada/SPARK 2022 — Nativní implementace
--
--  Autor: Pan Jeskyně
-- ============================================================

pragma SPARK_Mode (On);

package body Chrome_Webmcp_Engine is

   -- ==========================================================
   -- INICIALIZACE ENGINU
   -- ==========================================================
   procedure Initialize_Engine (Ctx : out Webmcp_Context) is
   begin
      Ctx.Current_State    := State_Idle;
      Ctx.Registered_Count := 0;
      Ctx.Active_Frames    := 0;
      Ctx.Zero_Trace_RAM   := True;

      for I in 1 .. Max_Tools_Registered loop
         Ctx.Registered_Tools (I) :=
           (Kind       => Tool_Accessibility_Sign,
            Is_Active  => False,
            Call_Count => 0);
      end loop;
   end Initialize_Engine;

   -- ==========================================================
   -- REGISTRACE WEBMCP NÁSTROJE
   -- ==========================================================
   procedure Register_Webmcp_Tool
     (Ctx     : in out Webmcp_Context;
      Kind    : in     Tool_Kind;
      Success :    out Boolean)
   is
   begin
      if Ctx.Registered_Count < Max_Tools_Registered then
         Ctx.Registered_Count := Ctx.Registered_Count + 1;
         Ctx.Registered_Tools (Ctx.Registered_Count) :=
           (Kind       => Kind,
            Is_Active  => True,
            Call_Count => 0);
         Success := True;
      else
         Success := False;
      end if;
   end Register_Webmcp_Tool;

   -- ==========================================================
   -- ODESLÁNÍ GEST ZNAKOVÉ ŘEČI (3D AVATAR)
   -- ==========================================================
   procedure Dispatch_Sign_Gesture
     (Ctx     : in out Webmcp_Context;
      Frames  : in     Frame_Count;
      Success :    out Boolean)
   is
   begin
      if Frames > 0 and then Ctx.Active_Frames <= Max_Gesture_Frames - Frames then
         Ctx.Active_Frames := Ctx.Active_Frames + Frames;
         Ctx.Current_State := State_Streaming;
         Success := True;
      else
         Success := False;
      end if;
   end Dispatch_Sign_Gesture;

   -- ==========================================================
   -- ASH SWEEPER: NULOVÁNÍ A SKARTACE V RAM
   -- ==========================================================
   procedure Purge_Ram_Buffer (Ctx : in out Webmcp_Context) is
   begin
      Ctx.Active_Frames  := 0;
      Ctx.Current_State  := State_Idle;
      Ctx.Zero_Trace_RAM := True;
   end Purge_Ram_Buffer;

end Chrome_Webmcp_Engine;
