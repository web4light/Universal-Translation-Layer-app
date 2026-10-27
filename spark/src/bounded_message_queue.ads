--  =============================================================================
--  Asterisk Gateway — Bounded Message Queue
--  SPARK 2022 Level 4 Gold (DO-178C DAL-A Compliant)
--  Deterministic zero-heap FIFO ring buffer for agentic message passing.
--  Standard 700: Memory-safe inter-task telemetry & prompt pipeline.
--  =============================================================================

package Bounded_Message_Queue with
  SPARK_Mode => On
is
   Queue_Capacity : constant := 32;
   subtype Queue_Index is Positive range 1 .. Queue_Capacity;
   subtype Element_Count is Natural range 0 .. Queue_Capacity;

   type Message_ID is mod 2**32;
   subtype Payload_String is String (1 .. 64);

   type Queue_Message is record
      Msg_ID  : Message_ID;
      Length  : Natural;
      Payload : Payload_String;
   end record;

   type Message_Array is array (Queue_Index) of Queue_Message;

   type FIFO_Queue is record
      Buffer : Message_Array;
      Head   : Queue_Index;
      Tail   : Queue_Index;
      Count  : Element_Count;
   end record;

   --  Initializes an empty FIFO queue with zero dynamic memory allocation.
   procedure Initialize_Queue
     (Q : out FIFO_Queue)
   with
     Global => null,
     Depends => (Q => null),
     Post => Q.Count = 0 and then
             Q.Head = 1 and then
             Q.Tail = 1;

   --  Enqueues a message into the ring buffer if not full.
   procedure Enqueue
     (Q       : in out FIFO_Queue;
      Item    : in     Queue_Message;
      Success : out    Boolean)
   with
     Global => null,
     Depends => (Q       => (Q, Item),
                 Success => Q),
     Post => (if Success then
                Q.Count = Q.Count'Old + 1 and then
                Q.Count <= Queue_Capacity
              else
                Q = Q'Old);

   --  Dequeues a message from the ring buffer if not empty.
   procedure Dequeue
     (Q       : in out FIFO_Queue;
      Item    : out    Queue_Message;
      Success : out    Boolean)
   with
     Global => null,
     Depends => ((Q, Item, Success) => Q),
     Post => (if Success then
                Q.Count = Q.Count'Old - 1 and then
                Q.Count <= Queue_Capacity
              else
                Q = Q'Old);

end Bounded_Message_Queue;
