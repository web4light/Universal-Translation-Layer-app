--  =============================================================================
--  Asterisk Gateway — Token Bucket Governor Implementation
--  SPARK 2022 Level 4 Gold (DO-178C DAL-A Compliant)
--  =============================================================================

package body Token_Bucket_Governor with
  SPARK_Mode => On
is

   procedure Initialize_Bucket
     (Bucket   : out Bucket_State;
      Capacity : in  Token_Count;
      Rate_Sec : in  Refill_Rate)
   is
   begin
      Bucket := (Capacity       => Capacity,
                 Current_Tokens => Capacity,
                 Refill_Per_Sec => Rate_Sec);
   end Initialize_Bucket;

   procedure Refill_Tokens
     (Bucket       : in out Bucket_State;
      Elapsed_Secs : in     Time_Delta)
   is
      Added_Tokens : constant Natural := Elapsed_Secs * Bucket.Refill_Per_Sec;
   begin
      if Added_Tokens >= Bucket.Capacity - Bucket.Current_Tokens then
         Bucket.Current_Tokens := Bucket.Capacity;
      else
         Bucket.Current_Tokens := Bucket.Current_Tokens + Added_Tokens;
      end if;
   end Refill_Tokens;

   procedure Consume_Tokens
     (Bucket    : in out Bucket_State;
      Requested : in     Token_Count;
      Allowed   : out    Boolean)
   is
   begin
      if Requested <= Bucket.Current_Tokens then
         Bucket.Current_Tokens := Bucket.Current_Tokens - Requested;
         Allowed := True;
      else
         Allowed := False;
      end if;
   end Consume_Tokens;

end Token_Bucket_Governor;
