--  =============================================================================
--  Asterisk Gateway — Token Bucket Governor
--  SPARK 2022 Level 4 Gold (DO-178C DAL-A Compliant)
--  Zero heap rate-limiter and compute budget governor for autonomous agents.
--  Standard 700: Prevents runaway agent loops and DoS across WebMCP / mesh.
--  =============================================================================

package Token_Bucket_Governor with
  SPARK_Mode => On
is
   Max_Capacity    : constant := 10_000;
   Max_Refill_Rate : constant := 1_000;

   subtype Token_Count is Natural range 0 .. Max_Capacity;
   subtype Refill_Rate is Positive range 1 .. Max_Refill_Rate;
   subtype Time_Delta  is Natural range 0 .. 3600;

   type Bucket_State is record
      Capacity       : Token_Count;
      Current_Tokens : Token_Count;
      Refill_Per_Sec : Refill_Rate;
   end record;

   --  Initializes the token bucket governor with defined capacity and refill rate.
   procedure Initialize_Bucket
     (Bucket   : out Bucket_State;
      Capacity : in  Token_Count;
      Rate_Sec : in  Refill_Rate)
   with
     Global => null,
     Depends => (Bucket => (Capacity, Rate_Sec)),
     Post => Bucket.Capacity = Capacity and then
             Bucket.Current_Tokens = Capacity and then
             Bucket.Refill_Per_Sec = Rate_Sec;

   --  Refills tokens based on elapsed time without arithmetic overflow.
   procedure Refill_Tokens
     (Bucket       : in out Bucket_State;
      Elapsed_Secs : in     Time_Delta)
   with
     Global => null,
     Depends => (Bucket =>+ Elapsed_Secs),
     Pre  => Bucket.Current_Tokens <= Bucket.Capacity,
     Post => Bucket.Current_Tokens <= Bucket.Capacity and then
             Bucket.Capacity = Bucket.Capacity'Old and then
             Bucket.Refill_Per_Sec = Bucket.Refill_Per_Sec'Old and then
             Bucket.Current_Tokens >= Bucket.Current_Tokens'Old;

   --  Attempts to consume tokens for an agent operation.
   procedure Consume_Tokens
     (Bucket    : in out Bucket_State;
      Requested : in     Token_Count;
      Allowed   : out    Boolean)
   with
     Global => null,
     Depends => ((Bucket, Allowed) => (Bucket, Requested)),
     Pre  => Bucket.Current_Tokens <= Bucket.Capacity,
     Post => (if Allowed then
                Bucket.Current_Tokens = Bucket.Current_Tokens'Old - Requested and then
                Bucket.Capacity = Bucket.Capacity'Old and then
                Bucket.Refill_Per_Sec = Bucket.Refill_Per_Sec'Old
              else
                Bucket = Bucket'Old);

end Token_Bucket_Governor;
