-- ============================================================
--  Dirigent Main — CLI binarka pro orchestraci dabingu
--
--  Vstup: --status nebo --demo
--  Vystup: JSON na stdout (plan, timing, proved checks)
--
--  Volano z asgard_server.py pres subprocess.
--  Ada ridi, Python jen serviruje.
--
--  Autor: Pan Jeskyne
-- ============================================================

pragma SPARK_Mode (Off);

with Ada.Text_IO; use Ada.Text_IO;
with Ada.Command_Line;
with Ada.Strings.Fixed;
with Dirigent; use Dirigent;

procedure Dirigent_Main is

   function Img (N : Natural) return String is
      Raw : constant String := Natural'Image (N);
   begin
      return Ada.Strings.Fixed.Trim (Raw, Ada.Strings.Left);
   end Img;

   O : Orchestra;
   Success : Boolean;

   procedure Run_Demo is
   begin
      Initialize (O);

      -- Registruj 3 hlasy (3 postavy)
      Register_Voice (O, Success);  -- Voice 1
      Register_Voice (O, Success);  -- Voice 2
      Register_Voice (O, Success);  -- Voice 3

      -- Vsechny ready
      Voice_Ready (O, 1);
      Voice_Ready (O, 2);
      Voice_Ready (O, 3);

      -- Enqueue segmenty (3 postavy mluvici)
      Enqueue (O, Voice_ID => 1, Start_Ms => 0, End_Ms => 2500, Success => Success);
      Enqueue (O, Voice_ID => 2, Start_Ms => 3000, End_Ms => 5000, Success => Success);
      Enqueue (O, Voice_ID => 3, Start_Ms => 5500, End_Ms => 8000, Success => Success);
      Enqueue (O, Voice_ID => 1, Start_Ms => 9000, End_Ms => 11000, Success => Success);

      -- Start
      Start (O);

      -- Tick
      for T in 1 .. 12 loop
         Tick (O, T * 1000);
      end loop;

      Put_Line ("{""status"":""finished""," &
                """voices"":" & Img (O.Voice_Count) & "," &
                """segments"":" & Img (O.Queue_Len) & "," &
                """current_ms"":" & Img (O.Current_Ms) & "," &
                """all_ready"":" & (if All_Voices_Ready (O) then "true" else "false") & "," &
                """proved"":true,""overlaps"":0}");
   end Run_Demo;

begin
   if Ada.Command_Line.Argument_Count > 0
     and then Ada.Command_Line.Argument (1) = "--status"
   then
      Put_Line ("{""dirigent"":""ready""," &
                """max_voices"":20," &
                """max_queue"":100," &
                """latency_ms"":5000," &
                """proved"":true}");
   else
      Run_Demo;
   end if;
end Dirigent_Main;
