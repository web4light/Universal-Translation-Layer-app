-- ============================================================
--  Web4 Identity — Implementation
--  "Ja jsem Groot." = jsi overeny.
--  "Ja jsem Groot." = nejsi. Pryc.
-- ============================================================

pragma SPARK_Mode (On);

package body Web4_Identity is

   procedure Register (NFT  : out Soulbound_NFT;
                       Kind : Entity_Kind;
                       ID   : Token_ID) is
   begin
      NFT := (ID           => ID,
              Kind         => Kind,
              State        => Unverified,
              Tier         => Free,
              Created_Day  => 1,
              Transferable => False);  -- Soulbound. Vzdy.
   end Register;

   procedure Verify (NFT : in out Soulbound_NFT) is
   begin
      NFT.State := Verified;
   end Verify;

   procedure Suspend (NFT : in out Soulbound_NFT) is
   begin
      NFT.State := Suspended;
   end Suspend;

   procedure Revoke (NFT : in out Soulbound_NFT) is
   begin
      NFT.State := Revoked;
   end Revoke;

   procedure Request_Verification (NFT : in out Soulbound_NFT) is
   begin
      NFT.State := Pending;
   end Request_Verification;

   function Can_Enter_Metaverse (NFT : Soulbound_NFT) return Boolean is
   begin
      return NFT.State = Verified and NFT.Transferable = False;
   end Can_Enter_Metaverse;

   function Is_Soulbound (NFT : Soulbound_NFT) return Boolean is
   begin
      return NFT.Transferable = False;
   end Is_Soulbound;

   procedure Count_Verified is
   begin
      Stats.Total_Verified := Stats.Total_Verified + 1;
   end Count_Verified;

   procedure Count_Bot_Rejected is
   begin
      Stats.Bots_Rejected := Stats.Bots_Rejected + 1;
   end Count_Bot_Rejected;

end Web4_Identity;
