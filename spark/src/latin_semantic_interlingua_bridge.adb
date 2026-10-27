--  =============================================================================
--  Latin_Semantic_Interlingua_Bridge - Implementation
--  =============================================================================

package body Latin_Semantic_Interlingua_Bridge with
  SPARK_Mode => On
is

   procedure Initialize_Bridge
     (Bridge : out Bridge_State)
   is
   begin
      Bridge := (Tokens_Buffered   => 0,
                 Tokens            => (others => Null_Token),
                 Is_Wire_Ready     => False,
                 Total_Bridged_P2P => 0);
   end Initialize_Bridge;

   procedure Append_Semantic_Pivot
     (Bridge    : in out Bridge_State;
      Lemma     : in     Lemma_Id_Type;
      Case_Kind : in     Latin_Grammatical_Case;
      Emphasis  : in     Emphasis_Range;
      Success   : out    Boolean)
   is
   begin
      if Bridge.Tokens_Buffered < 64 then
         Bridge.Tokens_Buffered := Bridge.Tokens_Buffered + 1;
         Bridge.Tokens (Bridge.Tokens_Buffered) :=
           (Lemma        => Lemma,
            Case_Kind    => Case_Kind,
            Emphasis_Pct => Emphasis);
         Bridge.Is_Wire_Ready := True;
         Success := True;
      else
         Success := False;
      end if;
   end Append_Semantic_Pivot;

   procedure Dispatch_P2P_Wire
     (Bridge  : in out Bridge_State;
      Flushed : out    Natural)
   is
   begin
      Flushed := Bridge.Tokens_Buffered;
      Bridge.Total_Bridged_P2P := Bridge.Total_Bridged_P2P + Bridge.Tokens_Buffered;
      Bridge.Tokens_Buffered   := 0;
      Bridge.Is_Wire_Ready     := False;
      Bridge.Tokens            := (others => Null_Token);
   end Dispatch_P2P_Wire;

end Latin_Semantic_Interlingua_Bridge;
