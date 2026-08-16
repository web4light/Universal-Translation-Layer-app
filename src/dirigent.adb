-- ============================================================
--  Dirigent — Implementation
-- ============================================================

pragma SPARK_Mode (On);

package body Dirigent is

   procedure Initialize (O : out Orchestra) is
   begin
      O.State       := Idle;
      O.Voice_Count := 0;
      O.Queue_Len   := 0;
      O.Current_Ms  := 0;
      O.Voices      := (others => (State => Unknown, Extracted => False));
      O.Queue       := (others => (Voice_ID => 0, Start_Ms => 0,
                                    End_Ms => 0, Filled => False));
   end Initialize;

   procedure Register_Voice (O       : in out Orchestra;
                             Success : out Boolean) is
   begin
      if O.Voice_Count >= Max_Voices then
         Success := False;
         return;
      end if;

      O.Voice_Count := O.Voice_Count + 1;
      O.Voices (O.Voice_Count) := (State     => Extracting,
                                    Extracted => False);
      Success := True;
   end Register_Voice;

   procedure Voice_Ready (O        : in out Orchestra;
                          Voice_ID : Voice_Index) is
   begin
      O.Voices (Voice_ID).State := Ready;
      O.Voices (Voice_ID).Extracted := True;
   end Voice_Ready;

   procedure Enqueue (O        : in out Orchestra;
                      Voice_ID : Voice_Index;
                      Start_Ms : Time_Ms;
                      End_Ms   : Time_Ms;
                      Success  : out Boolean) is
   begin
      if O.Queue_Len >= Max_Queue or End_Ms <= Start_Ms then
         Success := False;
         return;
      end if;

      O.Queue_Len := O.Queue_Len + 1;
      O.Queue (O.Queue_Len) := (Voice_ID => Voice_ID,
                                 Start_Ms => Start_Ms,
                                 End_Ms   => End_Ms,
                                 Filled   => True);
      Success := True;
   end Enqueue;

   function Can_Play (O   : Orchestra;
                      Idx : Queue_Index) return Boolean is
      Seg : Dub_Segment renames O.Queue (Idx);
   begin
      if not Seg.Filled then
         return False;
      end if;

      if Seg.Voice_ID < 1 or Seg.Voice_ID > O.Voice_Count then
         return False;
      end if;

      -- Hlas musí být ready
      if O.Voices (Seg.Voice_ID).State /= Ready then
         return False;
      end if;

      -- Timing: aktuální čas musí být >= start - buffer
      if O.Current_Ms + Buffer_Ms < Seg.Start_Ms then
         return False;
      end if;

      return True;
   end Can_Play;

   procedure Start (O : in out Orchestra) is
   begin
      O.State := Buffering;
   end Start;

   procedure Tick (O      : in out Orchestra;
                   Now_Ms : Time_Ms) is
   begin
      O.Current_Ms := Now_Ms;

      -- Přepnout z Buffering na Running po naplnění bufferu
      if O.State = Buffering and Now_Ms >= Buffer_Ms then
         O.State := Running;
      end if;
   end Tick;

   function All_Voices_Ready (O : Orchestra) return Boolean is
   begin
      for I in 1 .. O.Voice_Count loop
         if O.Voices (I).State /= Ready then
            return False;
         end if;
      end loop;
      return True;
   end All_Voices_Ready;

end Dirigent;
