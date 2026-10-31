#include "PBX/PBXCore.h"
#include "Misc/Paths.h"

// ------------------------------------------------------------------ cards
FString FPBXCardDef::EchoTexturePath() const
{
	const FString N = TEXT("T_Echo_") + Id.ToString();
	return FString::Printf(TEXT("/Game/PBX/Echo/%s.%s"), *N, *N);
}

FString FPBXCardDef::CardImagePath() const
{
	return FPaths::ConvertRelativePathToFull(FPaths::ProjectDir() / TEXT("../pokemon-card-scraper/pokemon_cards/images") / (Id.ToString() + TEXT(".jpg")));
}

namespace PBXData
{
	const TArray<FPBXCardDef>& Cards()
	{
		static TArray<FPBXCardDef> C;
		if (C.Num() == 0)
		{
			auto Add = [](const TCHAR* Id, const TCHAR* Name, const TCHAR* Type, int32 HP, int32 Atk, int32 Spd, int32 R, float Size)
			{
				FPBXCardDef D; D.Id = Id; D.Name = Name; D.Type = Type; D.HP = HP; D.Atk = Atk; D.Spd = Spd; D.Rarity = R; D.Size = Size; C.Add(D);
			};
			// Sigil & Spark (2026-10-31): the card ids stay (saves store them), every entry is now an ORIGINAL Spark with its own
			// 3D model (Quaternius Ultimate Monsters, CC0). Names / Inks: SIGIL_AND_SPARK.md §5.
			auto S = [&Add](const TCHAR* Id, const TCHAR* Name, const TCHAR* Type, int32 HP, int32 Atk, int32 Spd, int32 R, float Size, const TCHAR* Model)
			{ Add(Id, Name, Type, HP, Atk, Spd, R, Size); C.Last().Creature = Model; };
			// the three Sparks that hid in the Scriptorium (starters)
			S(TEXT("Bulbasaur_MEW_001"), TEXT("Sporrow"), TEXT("Grass"), 130, 59, 84, 2, 1.0f, TEXT("Blob/Mushnub"));
			S(TEXT("Charmander_MEW_004"), TEXT("Cindril"), TEXT("Fire"), 130, 60, 75, 3, 1.05f, TEXT("Flying/Dragon"));
			S(TEXT("Squirtle_PGO_015"), TEXT("Glublet"), TEXT("Water"), 100, 45, 94, 1, 1.0f, TEXT("Flying/Glub"));
			// wild Sparks of the west road
			S(TEXT("Pidgey_OBF_162"), TEXT("Coobit"), TEXT("Colorless"), 100, 49, 48, 0, .85f, TEXT("Blob/Pigeon"));
			S(TEXT("Lechonk_PAF_071"), TEXT("Barklet"), TEXT("Colorless"), 100, 50, 78, 0, .85f, TEXT("Blob/Dog"));
			S(TEXT("Starly_SVI_148"), TEXT("Puffchirp"), TEXT("Colorless"), 100, 51, 72, 0, .8f, TEXT("Blob/Birb"));
			S(TEXT("Jigglypuff_MEW_039"), TEXT("Blushy"), TEXT("Psychic"), 90, 35, 43, 0, .8f, TEXT("Blob/PinkBlob"));
			S(TEXT("Spearow_MEW_021"), TEXT("Purrsk"), TEXT("Colorless"), 100, 36, 90, 0, .85f, TEXT("Blob/Cat"));
			// Rho's partner
			S(TEXT("Eevee_MEW_133"), TEXT("Alpuff"), TEXT("Colorless"), 110, 46, 70, 0, .9f, TEXT("Flying/Alpaking"));
			// Route 1
			S(TEXT("Pidgey_MEW_016"), TEXT("Duskwing"), TEXT("Darkness"), 100, 45, 56, 0, .8f, TEXT("Flying/Pigeon"));
			S(TEXT("Pidgeotto_MEW_017"), TEXT("Stormbill"), TEXT("Lightning"), 120, 60, 71, 1, 1.0f, TEXT("Big/Birb"));
			S(TEXT("Rattata_MEW_019"), TEXT("Frostub"), TEXT("Fighting"), 90, 50, 72, 0, .7f, TEXT("Blob/Yeti"));
			S(TEXT("Caterpie_MEW_010"), TEXT("Mossle"), TEXT("Grass"), 90, 32, 45, 0, .7f, TEXT("Blob/GreenBlob"));
			S(TEXT("Metapod_MEW_011"), TEXT("Pricklet"), TEXT("Grass"), 115, 22, 30, 0, .8f, TEXT("Blob/Cactoro"));
			S(TEXT("Weedle_MEW_013"), TEXT("Burrhook"), TEXT("Metal"), 90, 36, 50, 0, .7f, TEXT("Blob/GreenSpikyBlob"));
			S(TEXT("Kakuna_MEW_014"), TEXT("Pebblit"), TEXT("Metal"), 115, 26, 35, 0, .8f, TEXT("Flying/Goleling"));
			S(TEXT("Nidoran_Female_MEW_029"), TEXT("Glimmo"), TEXT("Psychic"), 100, 47, 41, 0, .75f, TEXT("Blob/Alien"));
			S(TEXT("Nidoran_Male_MEW_032"), TEXT("Sparkcluck"), TEXT("Lightning"), 100, 57, 50, 0, .75f, TEXT("Blob/Chicken"));
			S(TEXT("Oddish_MEW_043"), TEXT("Croakra"), TEXT("Water"), 100, 50, 30, 0, .7f, TEXT("Big/Frog"));
			S(TEXT("Pikachu_MEW_025"), TEXT("Zumblet"), TEXT("Lightning"), 100, 55, 90, 2, .75f, TEXT("Flying/Armabee"));
		}
		return C;
	}
	const FPBXCardDef* Card(FName Id) { return Cards().FindByPredicate([&](const FPBXCardDef& D) { return D.Id == Id; }); }
	TArray<FName> Starters() { return { TEXT("Bulbasaur_MEW_001"), TEXT("Charmander_MEW_004"), TEXT("Squirtle_PGO_015") }; }
	TArray<FName> WildPool() { return { TEXT("Pidgey_OBF_162"), TEXT("Lechonk_PAF_071"), TEXT("Starly_SVI_148"), TEXT("Jigglypuff_MEW_039"), TEXT("Spearow_MEW_021") }; }
	FName RivalCard() { return TEXT("Eevee_MEW_133"); }
	FLinearColor TypeColor(const FString& T)
	{
		static const TMap<FString, FColor> M = { {TEXT("Grass"), FColor(0x5f, 0xae, 0x4f)}, {TEXT("Fire"), FColor(0xe8, 0x60, 0x3c)}, {TEXT("Water"), FColor(0x3d, 0x8f, 0xd6)},
			{TEXT("Lightning"), FColor(0xf2, 0xc2, 0x30)}, {TEXT("Psychic"), FColor(0xb0, 0x5f, 0xc9)}, {TEXT("Fighting"), FColor(0xb5, 0x67, 0x3a)}, {TEXT("Darkness"), FColor(0x3f, 0x4a, 0x5a)},
			{TEXT("Metal"), FColor(0x8e, 0x9a, 0xa6)}, {TEXT("Dragon"), FColor(0xc2, 0x9a, 0x2c)}, {TEXT("Colorless"), FColor(0xc9, 0xc2, 0xb0)} };
		const FColor* C = M.Find(T); return FLinearColor(C ? *C : FColor(200, 200, 200));
	}
	FString InkName(const FString& T)
	{
		static const TMap<FString, FString> M = { {TEXT("Fire"), TEXT("Ember")}, {TEXT("Water"), TEXT("Tide")}, {TEXT("Grass"), TEXT("Bloom")}, {TEXT("Lightning"), TEXT("Volt")},
			{TEXT("Psychic"), TEXT("Wisp")}, {TEXT("Fighting"), TEXT("Stone")}, {TEXT("Metal"), TEXT("Stone")}, {TEXT("Darkness"), TEXT("Dusk")}, {TEXT("Dragon"), TEXT("Ember")}, {TEXT("Colorless"), TEXT("Gale")} };
		const FString* F = M.Find(T); return F ? *F : T;
	}
	float LvMult(int32 Lv) { return .72f + Lv * .0125f; }
	int32 StartLevel(const FPBXCardDef& C) { return 10 + C.Rarity * 2; }   // council S6: the partner was Lv 18 on Route 1 (wild 8-15) — fights had no tension
}

// ------------------------------------------------------------------ fighters
FPBXFighter FPBXFighter::Make(const FPBXCardDef& C, int32 Lv, float L)
{
	FPBXFighter F; F.CardId = C.Id; F.Name = C.Name; F.Type = C.Type; F.Lv = Lv;
	F.MaxHP = F.HP = FMath::RoundToInt(C.HP * L); F.Atk = FMath::RoundToInt(C.Atk * L);
	F.Def = FMath::RoundToInt(C.HP * .25f + C.Atk * .2f); F.Spd = C.Spd;
	return F;
}

// ------------------------------------------------------------------ rules
float FPBXBattle::Mult(const FString& A, const FString& D)
{
	static const TMap<FString, TArray<FString>> Weak = {
		{TEXT("Fire"), {TEXT("Grass"), TEXT("Metal")}}, {TEXT("Water"), {TEXT("Fire")}}, {TEXT("Grass"), {TEXT("Water"), TEXT("Fighting")}},
		{TEXT("Lightning"), {TEXT("Water"), TEXT("Colorless")}}, {TEXT("Fighting"), {TEXT("Lightning"), TEXT("Darkness"), TEXT("Colorless"), TEXT("Metal")}},
		{TEXT("Psychic"), {TEXT("Fighting")}}, {TEXT("Darkness"), {TEXT("Psychic")}}, {TEXT("Metal"), {TEXT("Psychic"), TEXT("Fairy")}}, {TEXT("Dragon"), {TEXT("Dragon")}} };
	static const TMap<FString, TArray<FString>> Resist = {
		{TEXT("Fire"), {TEXT("Grass")}}, {TEXT("Water"), {TEXT("Fire"), TEXT("Metal")}}, {TEXT("Grass"), {TEXT("Water"), TEXT("Lightning")}},
		{TEXT("Lightning"), {TEXT("Metal")}}, {TEXT("Metal"), {TEXT("Grass")}}, {TEXT("Darkness"), {TEXT("Psychic")}} };
	float M = 1.f;
	if (const TArray<FString>* W = Weak.Find(A)) if (W->Contains(D)) M *= 1.5f;
	if (const TArray<FString>* R = Resist.Find(D)) if (R->Contains(A)) M *= .75f;
	return M;
}

const FPBXSig& FPBXBattle::SigOf(const FString& T)
{
	static const TMap<FString, FPBXSig> S = {   // Sigil & Spark Art names (effects unchanged)
		{TEXT("Fire"), {TEXT("Cinder Script"), TEXT("burn"), TEXT("burns for 3 turns")}}, {TEXT("Water"), {TEXT("Undertow"), TEXT("soak"), TEXT("lowers their speed")}},
		{TEXT("Grass"), {TEXT("Rootdrink"), TEXT("drain"), TEXT("heals 35% of damage")}}, {TEXT("Lightning"), {TEXT("Static Sigil"), TEXT("para"), TEXT("30% paralysis")}},
		{TEXT("Psychic"), {TEXT("Hush"), TEXT("weaken"), TEXT("lowers their attack")}}, {TEXT("Fighting"), {TEXT("Rockbreak"), TEXT("pierce"), TEXT("ignores guard")}},
		{TEXT("Darkness"), {TEXT("Nightquill"), TEXT("crit"), TEXT("high critical chance")}}, {TEXT("Metal"), {TEXT("Bulwark"), TEXT("shield"), TEXT("raises your defense")}},
		{TEXT("Dragon"), {TEXT("Wyrmfire"), TEXT("none"), TEXT("massive power")}}, {TEXT("Colorless"), {TEXT("Gust Rune"), TEXT("none"), TEXT("reliable damage")}} };
	const FPBXSig* F = S.Find(T); return F ? *F : S[TEXT("Colorless")];
}

int32 FPBXBattle::Power(EPBXMove M) { return M == EPBXMove::Attack ? 30 : M == EPBXMove::Sig ? 58 : M == EPBXMove::Ult ? 92 : 0; }
int32 FPBXBattle::Cost(EPBXMove M) { return M == EPBXMove::Sig ? 2 : M == EPBXMove::Ult ? 4 : 0; }
int32 FPBXBattle::Gain(EPBXMove M) { return (M == EPBXMove::Attack || M == EPBXMove::Guard) ? 1 : 0; }

int32 FPBXBattle::Estimate(const FPBXFighter& A, const FPBXFighter& D, EPBXMove M) const
{
	const int32 P = Power(M); if (!P) return 0;
	return FMath::RoundToInt(P * (A.Atk * A.BuffAtk) / (D.Def * D.BuffDef + 40.f) * 1.22f * Mult(A.Type, D.Type));
}

FPBXEvent FPBXBattle::Damage(FPBXFighter& Att, FPBXFighter& Def, EPBXMove M)
{
	const FPBXSig* Sig = M == EPBXMove::Sig ? &SigOf(Att.Type) : nullptr;
	const float Type = Mult(Att.Type, Def.Type), Roll = .9f + FMath::FRand() * .15f;
	const float CritP = (Sig && Sig->Fx == TEXT("crit")) ? .3f : .06f; const float Crit = FMath::FRand() < CritP ? 1.5f : 1.f;
	float D = Power(M) * (Att.Atk * Att.BuffAtk) / (Def.Def * Def.BuffDef + 40.f) * 1.22f * Type * Roll * Crit;
	const bool Pierce = Sig && Sig->Fx == TEXT("pierce");
	if (Def.bGuard && !Pierce) D *= .45f;
	FPBXEvent E; E.Kind = FPBXEvent::Hit; E.Dmg = FMath::Max(3, FMath::RoundToInt(D)); E.bEff = Type > 1.f; E.bWeak = Type < 1.f; E.bCrit = Crit > 1.f; E.bGuarded = Def.bGuard && !Pierce;
	return E;
}

FPBXBattle::FAct FPBXBattle::AiAction()
{
	FPBXFighter& Me = Active(1); const FPBXFighter& Foe = Active(0);
	TArray<int32> Bench; for (int32 i = 0; i < Team[1].Num(); i++) if (i != Act[1] && Team[1][i].HP > 0) Bench.Add(i);
	if (Mult(Foe.Type, Me.Type) > 1.f && Me.HP < Me.MaxHP * .5f && Bench.Num() && FMath::FRand() < .45f)
	{
		int32 Good = Bench[0]; for (int32 i : Bench) if (Mult(Foe.Type, Team[1][i].Type) <= 1.f) { Good = i; break; }
		return { EPBXMove::Switch, Good };
	}
	if (CanUse(Me, EPBXMove::Ult) && (FMath::FRand() < .7f || Foe.HP < Estimate(Me, Foe, EPBXMove::Ult))) return { EPBXMove::Ult, -1 };
	if (CanUse(Me, EPBXMove::Sig) && (Foe.HP <= Estimate(Me, Foe, EPBXMove::Sig) || FMath::FRand() < .35f)) return { EPBXMove::Sig, -1 };
	if (Me.HP < Me.MaxHP * .35f && !Me.bGuard && FMath::FRand() < .3f) return { EPBXMove::Guard, -1 };
	return { EPBXMove::Attack, -1 };
}

TArray<FPBXEvent> FPBXBattle::Round(EPBXMove PlayerMove, int32 SwitchTo)
{
	TArray<FPBXEvent> Ev; FAct Acts[2]; Acts[0] = { PlayerMove, SwitchTo }; Acts[1] = AiAction();
	for (int32 S = 0; S < 2; S++) if (Acts[S].Kind == EPBXMove::Switch && Acts[S].To >= 0)
	{
		Active(S).bGuard = false; Act[S] = Acts[S].To; FPBXEvent E; E.Kind = FPBXEvent::Switch; E.Side = S; E.To = Acts[S].To; Ev.Add(E);
	}
	for (int32 S = 0; S < 2; S++) Active(S).bGuard = false;
	for (int32 S = 0; S < 2; S++) if (Acts[S].Kind == EPBXMove::Guard)
	{
		FPBXFighter& F = Active(S); F.bGuard = true; F.Energy = FMath::Min(EnergyMax, F.Energy + 1); FPBXEvent E; E.Kind = FPBXEvent::Guard; E.Side = S; Ev.Add(E);
	}
	auto Spd = [&](int32 S) { return Active(S).Spd * Active(S).BuffSpd; };
	int32 Order[2] = { 0, 1 };
	if (Spd(1) > Spd(0) || (Spd(1) == Spd(0) && FMath::RandBool())) { Order[0] = 1; Order[1] = 0; }
	bool Skip[2] = { false, false };
	for (int32 k = 0; k < 2; k++)
	{
		const int32 S = Order[k];
		if (!Over.IsEmpty()) break;
		if (Skip[S]) continue;
		FAct& A = Acts[S]; FPBXFighter& Me = Active(S); const int32 O = 1 - S; FPBXFighter& Foe = Active(O);
		if (Me.HP <= 0 || Power(A.Kind) == 0) continue;
		if (!CanUse(Me, A.Kind)) A.Kind = EPBXMove::Attack;
		if (Me.Status == TEXT("para") && FMath::FRand() < .3f) { FPBXEvent E; E.Kind = FPBXEvent::Para; E.Side = S; Ev.Add(E); continue; }
		Me.Energy = FMath::Clamp(Me.Energy - Cost(A.Kind) + Gain(A.Kind), 0, EnergyMax);
		FPBXEvent R = Damage(Me, Foe, A.Kind);
		Foe.HP = FMath::Max(Foe.MinHP, Foe.HP - R.Dmg);
		const FPBXSig* Sig = A.Kind == EPBXMove::Sig ? &SigOf(Me.Type) : nullptr;
		R.Side = S; R.MoveKind = A.Kind; R.Type = Me.Type;
		R.Move = A.Kind == EPBXMove::Attack ? TEXT("Attack") : A.Kind == EPBXMove::Ult ? TEXT("Ultimate") : Sig->Name;
		Ev.Add(R);
		if (Sig && Foe.HP > 0)
		{
			FPBXEvent E; E.Side = O;
			if (Sig->Fx == TEXT("burn") && Foe.Status.IsNone()) { Foe.Status = TEXT("burn"); Foe.StatusT = 3; E.Kind = FPBXEvent::Status; E.St = Foe.Status; Ev.Add(E); }
			else if (Sig->Fx == TEXT("para") && Foe.Status.IsNone() && FMath::FRand() < .3f) { Foe.Status = TEXT("para"); Foe.StatusT = 2; E.Kind = FPBXEvent::Status; E.St = Foe.Status; Ev.Add(E); }
			else if (Sig->Fx == TEXT("soak")) { Foe.BuffSpd = FMath::Max(.6f, Foe.BuffSpd - .2f); E.Kind = FPBXEvent::Debuff; E.Stat = TEXT("SPD"); Ev.Add(E); }
			else if (Sig->Fx == TEXT("weaken")) { Foe.BuffAtk = FMath::Max(.6f, Foe.BuffAtk - .15f); E.Kind = FPBXEvent::Debuff; E.Stat = TEXT("ATK"); Ev.Add(E); }
		}
		if (Sig && Sig->Fx == TEXT("drain")) { const int32 H = FMath::RoundToInt(R.Dmg * .35f); Me.HP = FMath::Min(Me.MaxHP, Me.HP + H); FPBXEvent E; E.Kind = FPBXEvent::Heal; E.Side = S; E.Dmg = H; Ev.Add(E); }
		if (Sig && Sig->Fx == TEXT("shield")) { Me.BuffDef = FMath::Min(1.6f, Me.BuffDef + .2f); FPBXEvent E; E.Kind = FPBXEvent::Buff; E.Side = S; E.Stat = TEXT("DEF"); Ev.Add(E); }
		if (KO(O, S, Ev, Skip)) break;
	}
	for (int32 S = 0; S < 2; S++)
	{
		if (!Over.IsEmpty()) break;
		FPBXFighter& F = Active(S); if (F.HP <= 0 || F.Status.IsNone()) continue;
		if (F.Status == TEXT("burn"))
		{
			const int32 D = FMath::Max(4, FMath::RoundToInt(F.MaxHP * .06f)); F.HP = FMath::Max(F.MinHP, F.HP - D);
			FPBXEvent E; E.Kind = FPBXEvent::Burn; E.Side = S; E.Dmg = D; Ev.Add(E);
			if (KO(S, 1 - S, Ev, Skip)) break;
		}
		if (--F.StatusT <= 0) { FPBXEvent E; E.Kind = FPBXEvent::Cure; E.Side = S; E.St = F.Status; Ev.Add(E); F.Status = NAME_None; }
	}
	Turn++;
	return Ev;
}

bool FPBXBattle::KO(int32 O, int32 Winner, TArray<FPBXEvent>& Ev, bool Skip[2])
{
	if (Active(O).HP > 0) return false;
	{ FPBXEvent E; E.Kind = FPBXEvent::KO; E.Side = O; Ev.Add(E); }
	int32 Next = -1; for (int32 i = 0; i < Team[O].Num(); i++) if (Team[O][i].HP > 0) { Next = i; break; }
	if (Next < 0) { Over = Winner == 0 ? TEXT("win") : TEXT("lose"); FPBXEvent E; E.Kind = FPBXEvent::End; E.Result = Over; Ev.Add(E); return true; }
	Act[O] = Next; Skip[O] = true; FPBXEvent E; E.Kind = FPBXEvent::Switch; E.Side = O; E.To = Next; E.bForced = true; Ev.Add(E);
	return false;
}

float FPBXBattle::CaptureChance() const
{
	const FPBXFighter& F = Active(1); const FPBXCardDef* C = PBXData::Card(F.CardId);
	return FMath::Clamp(.22f + (1.f - float(F.HP) / F.MaxHP) * .72f - (C ? C->Rarity : 0) * .05f + (F.Status.IsNone() ? 0.f : .1f), .08f, .95f);
}
