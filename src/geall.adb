-- ================================================================
-- GEALL - Implementation
-- Ada orchestrator calling Gemini CLI
-- ================================================================

with Ada.Text_IO;          use Ada.Text_IO;
with GNAT.OS_Lib;
with GNAT.Expect;

package body Geall is

   use type Mincovna.Verification_Result;

   procedure Process_Message
     (User_Token : in     Mincovna.Token_String;
      Input      : in     String;
      Output     :    out Response)
   is
      Auth : constant Mincovna.Verification_Result :=
               Mincovna.Verify (User_Token);
   begin
      if Auth = Mincovna.Denied then
         Output := (Status  => Auth_Failed,
                    Message => (others => ' '),
                    Length  => 0);
         Put_Line ("[GEALL] Access denied - KYC failed");
         return;
      end if;

      Put_Line ("[GEALL] KYC OK - calling Gemini...");

      declare
         Args   : GNAT.OS_Lib.Argument_List :=
                    [1 => new String'("-p"),
                     2 => new String'(Input)];
         Pid    : GNAT.Expect.Process_Descriptor;
         Result : GNAT.Expect.Expect_Match;
         Gemini : constant String := "gemini";
      begin
         GNAT.Expect.Non_Blocking_Spawn
           (Pid, Gemini, Args);

         GNAT.Expect.Expect (Pid, Result, ".+", Timeout => 30_000);

         declare
            Raw : constant String := GNAT.Expect.Expect_Out (Pid);
            Len : constant Natural :=
                    Natural'Min (Raw'Length, Message_String'Length);
         begin
            Output.Status  := Success;
            Output.Length  := Len;
            Output.Message := (others => ' ');
            Output.Message (1 .. Len) := Raw (Raw'First .. Raw'First + Len - 1);
         end;

         GNAT.Expect.Close (Pid);

         for A of Args loop
            GNAT.OS_Lib.Free (A);
         end loop;

      exception
         when others =>
            Output := (Status  => Error,
                       Message => (others => ' '),
                       Length  => 0);
            Put_Line ("[GEALL] Error calling Gemini CLI");
      end;

   end Process_Message;

end Geall;