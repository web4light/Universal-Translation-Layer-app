--  =============================================================================
--  Asterisk Gateway — Bounded Message Queue Implementation
--  SPARK 2022 Level 4 Gold (DO-178C DAL-A Compliant)
--  =============================================================================

package body Bounded_Message_Queue with
  SPARK_Mode => On
is

   procedure Initialize_Queue
     (Q : out FIFO_Queue)
   is
      Empty_Msg : constant Queue_Message :=
        (Msg_ID  => 0,
         Length  => 0,
         Payload => (others => ' '));
   begin
      Q := (Buffer => (others => Empty_Msg),
            Head   => 1,
            Tail   => 1,
            Count  => 0);
   end Initialize_Queue;

   procedure Enqueue
     (Q       : in out FIFO_Queue;
      Item    : in     Queue_Message;
      Success : out    Boolean)
   is
   begin
      if Q.Count < Queue_Capacity then
         Q.Buffer (Q.Tail) := Item;
         if Q.Tail = Queue_Capacity then
            Q.Tail := 1;
         else
            Q.Tail := Q.Tail + 1;
         end if;
         Q.Count := Q.Count + 1;
         Success := True;
      else
         Success := False;
      end if;
   end Enqueue;

   procedure Dequeue
     (Q       : in out FIFO_Queue;
      Item    : out    Queue_Message;
      Success : out    Boolean)
   is
   begin
      if Q.Count > 0 then
         Item := Q.Buffer (Q.Head);
         if Q.Head = Queue_Capacity then
            Q.Head := 1;
         else
            Q.Head := Q.Head + 1;
         end if;
         Q.Count := Q.Count - 1;
         Success := True;
      else
         Item := (Msg_ID  => 0,
                  Length  => 0,
                  Payload => (others => ' '));
         Success := False;
      end if;
   end Dequeue;

end Bounded_Message_Queue;
