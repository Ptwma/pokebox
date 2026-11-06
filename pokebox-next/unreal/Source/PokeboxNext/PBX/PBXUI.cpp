#include "PBX/PBXUI.h"
#include "Widgets/Layout/SScaleBox.h"
#include "PBX/PBXCore.h"
#include "Widgets/SOverlay.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SSpacer.h"
#include "Widgets/Images/SImage.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/SCanvas.h"
#include "Brushes/SlateColorBrush.h"
#include "Brushes/SlateRoundedBoxBrush.h"
#include "Fonts/CompositeFont.h"
#include "Styling/CoreStyle.h"
#include "Engine/Texture2D.h"
#include "Misc/Paths.h"
#include "Widgets/SLeafWidget.h"
#include "Rendering/DrawElements.h"
#include "Framework/Application/SlateApplication.h"
#include "Fonts/FontMeasure.h"
#include "Rendering/SlateRenderer.h"
#include "ImageUtils.h"

static const FLinearColor InkC(.03f, .025f, .04f);
static const FLinearColor PaperC(1.f, .98f, .93f);
// 2026-11-01 "Codex" UI (Sigil & Spark): the whole UI is the Codex itself — parchment pages, hand-ruled ink frames, iron-gall
// ink text, crimson rubrics (the scribe's red), wax seals, dry-brush strokes. Matches the pen-and-ink legend intro.
static const FLinearColor GoldC(1.f, .80f, .42f);              // gold leaf: only over dark (ink wash, the world)
static const FLinearColor TextC(.10f, .065f, .045f);            // iron-gall ink on parchment
static const FLinearColor SepiaC(.36f, .25f, .16f);             // faded ink: secondary text on parchment
static const FLinearColor CrimsonC(.60f, .07f, .05f);           // rubric red: accents, selection, the speaker ribbon
static const FLinearColor IvoryC(.97f, .93f, .84f);             // text over the world / ink wash
static const FLinearColor GlassC(.06f, .045f, .035f, .80f);     // fallback panel when the Codex textures are missing
static const FLinearColor RimC(.60f, .07f, .05f, .8f);

FSlateFontInfo PBXUI::Font(const TCHAR* Kind, int32 Size, int32 Outline)
{
	static TMap<FString, TSharedPtr<const FCompositeFont>> Cache;
	const FString K = Kind;
	// 2026-11-01 Codex fonts (all SIL OFL, Google Fonts): Cinzel = Roman capitals for titles / labels, EB Garamond = book
	// text for HUD lines, IM Fell English = the old printed-book face for dialogue + subtitles. Barlow stays as fallback.
	const TCHAR* File = K == TEXT("title") ? TEXT("Cinzel-Bold.ttf") : K == TEXT("label") ? TEXT("Cinzel-Regular.ttf") : K == TEXT("bold") ? TEXT("EBGaramond-SemiBold.ttf")
		: K == TEXT("italic") ? TEXT("IMFellEnglish-Italic.ttf") : TEXT("IMFellEnglish-Regular.ttf");
	FString Path = FPaths::ProjectContentDir() / TEXT("PBX/Fonts") / File;
	if (!FPaths::FileExists(Path)) Path = FPaths::ProjectContentDir() / TEXT("PBX/Fonts") / (K == TEXT("body") || K == TEXT("italic") ? TEXT("BarlowCondensed-SemiBold.ttf") : TEXT("BarlowCondensed-ExtraBold.ttf"));
	TSharedPtr<const FCompositeFont>& F = Cache.FindOrAdd(Path);
	if (!F.IsValid())
	{
		if (FPaths::FileExists(Path)) F = MakeShared<FStandaloneCompositeFont>(NAME_None, Path, EFontHinting::Default, EFontLoadingPolicy::LazyLoad);
		else { FSlateFontInfo D = FCoreStyle::GetDefaultFontStyle(K == TEXT("body") ? "Regular" : "Bold", Size); if (Outline) { D.OutlineSettings.OutlineSize = Outline; D.OutlineSettings.OutlineColor = InkC; } return D; }
	}
	FSlateFontInfo I(F, Size);
	if (K == TEXT("title")) I.LetterSpacing = 40;                  // tracked Roman capitals
	if (K == TEXT("label")) I.LetterSpacing = 120;                 // small spaced capitals (chapter line, ENERGY)
	if (Outline) { I.OutlineSettings.OutlineSize = FMath::Max(1, Outline / 2); I.OutlineSettings.OutlineColor = FLinearColor(0, 0, 0, .6f); }
	return I;
}

TSharedPtr<FSlateBrush> PBXUI::TextureBrush(UTexture2D* T, FVector2D Size)
{
	TSharedPtr<FSlateBrush> B = MakeShared<FSlateBrush>();
	B->SetResourceObject(T); B->ImageSize = Size; B->DrawAs = ESlateBrushDrawType::Image;
	return B;
}

static const FSlateBrush* White() { return FCoreStyle::Get().GetBrush("WhiteBrush"); }

/** a Codex texture from Content/PBX/UI (tools/ui_codex_tex.py) as a 9-slice box (Margin > 0) or a plain image, drawn at
 *  Size px; cached for the whole session. Missing file -> a plain rounded panel so the UI still works. */
static const FSlateBrush* Codex(const TCHAR* Name, FVector2f Size, float Margin = 0.f)
{
	static TMap<FString, TSharedPtr<FSlateBrush>> Cache;
	const FString Key = FString::Printf(TEXT("%s|%.0f|%.0f|%.3f"), Name, Size.X, Size.Y, Margin);
	if (const TSharedPtr<FSlateBrush>* F = Cache.Find(Key)) return F->Get();
	const FString Path = FPaths::ConvertRelativePathToFull(FPaths::ProjectContentDir() / TEXT("PBX/UI") / (FString(Name) + TEXT(".png")));
	// r59 test: path-named Slate brushes are never loaded outside a registered style (they drew as plain white), so the
	// PNG is decoded into a transient UTexture2D (rooted, one per file) and the brush points at that object.
	static TMap<FString, UTexture2D*> Tex;
	UTexture2D* T = nullptr;
	if (UTexture2D** F = Tex.Find(Path)) T = *F;
	else
	{
		T = FPaths::FileExists(Path) ? FImageUtils::ImportFileAsTexture2D(Path) : nullptr;
		if (T) { T->AddToRoot(); T->Filter = TF_Trilinear; }
		else UE_LOG(LogTemp, Warning, TEXT("[PBXASSET] UI texture %s missing"), *Path);
		Tex.Add(Path, T);
	}
	TSharedPtr<FSlateBrush> B;
	if (!T) B = MakeShared<FSlateRoundedBoxBrush>(GlassC, 10.f, RimC, 1.5f);
	else
	{
		B = MakeShared<FSlateBrush>(); B->SetResourceObject(T); B->ImageSize = FVector2D(Size);
		B->DrawAs = Margin > 0.f ? ESlateBrushDrawType::Box : ESlateBrushDrawType::Image; B->Margin = FMargin(Margin);
	}
	Cache.Add(Key, B);
	return B.Get();
}
// r59: 9-slice margins follow the texture's own pixels, so the parchment is authored at its draw size: 192 px, ruled frame
// 15 px in, 24 px corners. Every parchment widget keeps its text >= 28 px from the edge.
static const FSlateBrush* Parchment(bool bSel = false, float = 0.f) { return Codex(bSel ? TEXT("ui_parchment_sel") : TEXT("ui_parchment"), FVector2f(192.f, 192.f), .125f); }
static const FSlateBrush* InkWash() { return Codex(TEXT("ui_inkwash"), FVector2f(256.f, 128.f), .14f); }
static const FSlateBrush* Stroke() { return Codex(TEXT("ui_stroke"), FVector2f(512.f, 64.f), 0.f); }
static const FSlateBrush* StrokeBox() { return Codex(TEXT("ui_stroke"), FVector2f(256.f, 32.f), .08f); }   // bars: keeps the tapered ends
static const FSlateBrush* Seal() { return Codex(TEXT("ui_seal"), FVector2f(64.f, 64.f), 0.f); }

// ------------------------------------------------------------------ UI particles
void PBXUI::SparkBurst(FPBXUIModel& M, FVector2D At, FLinearColor C, int32 N, float Speed, float Size)
{
	for (int32 i = 0; i < N && M.Sparks.Num() < 600; i++)
	{
		FPBXSpark S; S.P = At; const float A = FMath::FRand() * 2.f * PI; S.V = FVector2D(FMath::Cos(A), FMath::Sin(A)) * Speed * FMath::FRandRange(.3f, 1.f);
		S.C = C * FMath::FRandRange(.85f, 1.15f); S.C.A = 1.f; S.Size = Size * FMath::FRandRange(.5f, 1.3f); S.Life = FMath::FRandRange(.35f, .8f); S.Grav = 700.f;
		M.Sparks.Add(S);
	}
}

void PBXUI::Confetti(FPBXUIModel& M, int32 N)
{
	static const FLinearColor Cols[] = { FLinearColor(1, .82f, .2f), FLinearColor(.95f, .3f, .3f), FLinearColor(.3f, .7f, 1), FLinearColor(.4f, .9f, .4f), FLinearColor(1, 1, 1), FLinearColor(.9f, .5f, 1) };
	for (int32 i = 0; i < N && M.Sparks.Num() < 600; i++)
	{
		FPBXSpark S; S.P = FVector2D(FMath::FRand() * M.ViewSize.X, -FMath::FRand() * M.ViewSize.Y * .4f);
		S.V = FVector2D(FMath::FRandRange(-120.f, 120.f), FMath::FRandRange(180.f, 420.f)); S.C = Cols[FMath::RandRange(0, 5)];
		S.Size = FMath::FRandRange(10.f, 20.f); S.Life = FMath::FRandRange(2.5f, 4.f); S.Grav = 60.f; S.bConfetti = true; S.Phase = FMath::FRand() * 6.f; S.Spin = FMath::FRandRange(4.f, 10.f);
		M.Sparks.Add(S);
	}
}

void PBXUI::TickSparks(FPBXUIModel& M, float Dt)
{
	for (int32 i = M.Sparks.Num() - 1; i >= 0; i--)
	{
		FPBXSpark& S = M.Sparks[i]; S.Age += Dt;
		if (S.Age >= S.Life) { M.Sparks.RemoveAtSwap(i); continue; }
		S.V.Y += S.Grav * Dt; if (!S.bConfetti) S.V *= FMath::Max(0.f, 1.f - 2.2f * Dt);
		else S.V.X += FMath::Sin(S.Age * 3.f + S.Phase) * 90.f * Dt;
		S.P += S.V * Dt; S.Phase += S.Spin * Dt;
	}
}

// The intro's "ink myth" (Sigil & Spark): a dark page on which golden Script glyphs draw themselves. Modes: 1 one glyph
// writes itself in the middle · 2 glyphs spread over the page like a map of islands · 4 an open book whose pages fill with
// lines of glyphs · 5 the full page, erased by a white sweep (InkWipe 0..1). InkTitle = a big centred title.
class SPBXInk : public SLeafWidget
{
public:
	SLATE_BEGIN_ARGS(SPBXInk) {}
	SLATE_END_ARGS()
	void Construct(const FArguments&, TSharedPtr<FPBXUIModel> InM) { M = InM; }
	virtual FVector2D ComputeDesiredSize(float) const override { return FVector2D(8, 8); }
	static TArray<TArray<FVector2f>> Glyph(uint32 Seed)
	{
		FRandomStream R(Seed); TArray<TArray<FVector2f>> Strokes;
		const int32 NS = R.RandRange(2, 4);
		for (int32 s = 0; s < NS; s++)
		{
			TArray<FVector2f> P; FVector2f C(R.FRandRange(-.6f, .6f), R.FRandRange(-.8f, .8f)); float A = R.FRandRange(0.f, 6.28f);
			const int32 NP = R.RandRange(3, 6);
			for (int32 k = 0; k < NP; k++) { P.Add(C); A += R.FRandRange(-1.6f, 1.6f); C += FVector2f(FMath::Cos(A), FMath::Sin(A)) * R.FRandRange(.25f, .55f); C.X = FMath::Clamp(C.X, -1.f, 1.f); C.Y = FMath::Clamp(C.Y, -1.f, 1.f); }
			Strokes.Add(P);
		}
		return Strokes;
	}
	static void DrawGlyph(FSlateWindowElementList& Out, int32 Layer, const FGeometry& G, uint32 Seed, FVector2f At, float Size, float Reveal, FLinearColor C)
	{
		if (Reveal <= 0.f || C.A <= .01f) return;
		const TArray<TArray<FVector2f>> St = Glyph(Seed);
		float Total = 0.f; for (const TArray<FVector2f>& P : St) for (int32 k = 1; k < P.Num(); k++) Total += (P[k] - P[k - 1]).Size();
		float Budget = Total * FMath::Clamp(Reveal, 0.f, 1.f);
		for (const TArray<FVector2f>& P : St)
		{
			TArray<FVector2f> Pts; Pts.Add(At + P[0] * Size);
			for (int32 k = 1; k < P.Num() && Budget > 0.f; k++)
			{
				const float L = (P[k] - P[k - 1]).Size();
				const FVector2f E = L <= Budget ? P[k] : P[k - 1] + (P[k] - P[k - 1]) * (Budget / L);
				Pts.Add(At + E * Size); Budget -= L;
			}
			if (Pts.Num() < 2) break;
			FLinearColor Glow = C; Glow.A *= .22f;
			FSlateDrawElement::MakeLines(Out, Layer, G.ToPaintGeometry(), Pts, ESlateDrawEffect::None, Glow, true, FMath::Max(3.f, Size * .09f));
			FSlateDrawElement::MakeLines(Out, Layer + 1, G.ToPaintGeometry(), Pts, ESlateDrawEffect::None, C, true, FMath::Max(1.5f, Size * .03f));
		}
	}
	virtual int32 OnPaint(const FPaintArgs&, const FGeometry& G, const FSlateRect&, FSlateWindowElementList& Out, int32 Layer, const FWidgetStyle&, bool) const override
	{
		if (!M.IsValid() || M->Ink <= .001f) return Layer;
		const FVector2f S = FVector2f(G.GetLocalSize()); const float A = M->Ink, T = M->InkT;
		FSlateDrawElement::MakeBox(Out, Layer, G.ToPaintGeometry(), White(), ESlateDrawEffect::None, FLinearColor(.012f, .014f, .028f, A));
		const FLinearColor Gold(1.f, .78f, .38f, A);
		auto Wiped = [&](float X) { return M->InkMode == 5 && X / S.X < M->InkWipe * 1.25f - .1f; };
		if (M->InkMode == 1)
			DrawGlyph(Out, Layer + 1, G, 7, S * .5f, S.Y * .22f, T / 2.6f, Gold);
		else if (M->InkMode == 2 || M->InkMode == 5)
		{
			FRandomStream R(42);
			for (int32 i = 0; i < 46; i++)
			{
				const FVector2f P(R.FRandRange(.08f, .92f) * S.X, R.FRandRange(.12f, .88f) * S.Y);
				const float Delay = M->InkMode == 5 ? -10.f : R.FRandRange(0.f, 3.5f), Sz = R.FRandRange(.025f, .07f) * S.Y;
				FLinearColor C = Gold; C.A *= R.FRandRange(.45f, 1.f);
				if (Wiped(P.X)) continue;
				if (M->InkMode == 5 && P.X / S.X < M->InkWipe * 1.25f + .05f) C = FLinearColor(1, 1, 1, A);   // the white edge eats the glyphs
				DrawGlyph(Out, Layer + 1, G, 100 + i, P, Sz, (T - Delay) / 1.6f, C);
			}
			if (M->InkMode == 5)   // the white sweep itself
			{
				const float X = (M->InkWipe * 1.25f - .1f) * S.X;
				if (X > 0.f) FSlateDrawElement::MakeBox(Out, Layer + 3, G.ToPaintGeometry(FVector2f(FMath::Min(X, S.X), S.Y), FSlateLayoutTransform()), White(), ESlateDrawEffect::None, FLinearColor(.96f, .96f, .94f, A));
			}
		}
		else if (M->InkMode == 4)
		{
			const FVector2f C = S * .5f, Pg(S.Y * .42f, S.Y * .56f);
			for (int32 side = 0; side < 2; side++)
			{
				const FVector2f O = C + FVector2f(side ? 12.f : -12.f - Pg.X, -Pg.Y * .5f);
				TArray<FVector2f> Box = { O, O + FVector2f(Pg.X, 0), O + Pg, O + FVector2f(0, Pg.Y), O };
				FSlateDrawElement::MakeLines(Out, Layer + 1, G.ToPaintGeometry(), Box, ESlateDrawEffect::None, FLinearColor(1.f, .8f, .45f, .55f * A), true, 2.f);
				for (int32 row = 0; row < 7; row++) for (int32 col = 0; col < 6; col++)
				{
					const float Delay = (side * 42 + row * 6 + col) * .07f;
					DrawGlyph(Out, Layer + 2, G, 300 + side * 100 + row * 10 + col, O + FVector2f((col + .7f) * Pg.X / 6.6f, (row + .8f) * Pg.Y / 7.6f), Pg.X * .055f, (T - Delay) / .5f, Gold);
				}
			}
		}
		if (!M->InkTitle.IsEmpty())
		{
			const FSlateFontInfo F = PBXUI::Font(TEXT("title"), 96, 0);
			const float K = FMath::Clamp(T / 1.5f, 0.f, 1.f);
			const FVector2f TS = FVector2f(FSlateApplication::Get().GetRenderer()->GetFontMeasureService()->Measure(M->InkTitle, F));
			FSlateDrawElement::MakeText(Out, Layer + 4, G.ToPaintGeometry(TS, FSlateLayoutTransform(S * .5f - TS * .5f)),
				M->InkTitle, F, ESlateDrawEffect::None, FLinearColor(1.f, .86f, .52f, A * K));
		}
		return Layer + 5;
	}
private:
	TSharedPtr<FPBXUIModel> M;
};

class SPBXSparks : public SLeafWidget
{
public:
	SLATE_BEGIN_ARGS(SPBXSparks) {}
	SLATE_END_ARGS()
	void Construct(const FArguments&, TSharedPtr<FPBXUIModel> InM) { M = InM; Dot = MakeShared<FSlateRoundedBoxBrush>(FLinearColor::White, 64.f); }
	virtual FVector2D ComputeDesiredSize(float) const override { return FVector2D(8, 8); }
	virtual int32 OnPaint(const FPaintArgs&, const FGeometry& G, const FSlateRect&, FSlateWindowElementList& Out, int32 Layer, const FWidgetStyle&, bool) const override
	{
		if (!M.IsValid()) return Layer;
		for (const FPBXSpark& S : M->Sparks)
		{
			const float K = S.Age / S.Life; FLinearColor C = S.C; C.A = FMath::Clamp(S.bConfetti ? (1.f - FMath::Max(0.f, K - .8f) * 5.f) : 1.f - K * K, 0.f, 1.f);
			FVector2f Sz = S.bConfetti ? FVector2f(S.Size * FMath::Max(.15f, FMath::Abs(FMath::Cos(S.Phase))), S.Size * .6f) : FVector2f(S.Size * (1.f - K * .5f));
			if (!S.bConfetti)   // glow halo under each spark
			{
				FLinearColor H = C; H.A *= .25f; const FVector2f Hs = Sz * 2.6f;
				FSlateDrawElement::MakeBox(Out, Layer, G.ToPaintGeometry(Hs, FSlateLayoutTransform(FVector2f(S.P) - Hs * .5f)), Dot.Get(), ESlateDrawEffect::None, H);
			}
			FSlateDrawElement::MakeBox(Out, Layer + 1, G.ToPaintGeometry(Sz, FSlateLayoutTransform(FVector2f(S.P) - Sz * .5f)), S.bConfetti ? White() : Dot.Get(), ESlateDrawEffect::None, C);
		}
		return Layer + 1;
	}
private:
	TSharedPtr<FPBXUIModel> M; TSharedPtr<FSlateBrush> Dot;
};

// Scene changes (owner: "drawn pages, effects and light"): the screen is covered in ink that blots back from the edges
// and leaves the new page — irregular blobs, each shrinking at its own pace, a few drips; no texture needed.
class SPBXPageInk : public SLeafWidget
{
public:
	SLATE_BEGIN_ARGS(SPBXPageInk) {}
	SLATE_END_ARGS()
	void Construct(const FArguments&, TSharedPtr<FPBXUIModel> InM) { M = InM; Dot = MakeShared<FSlateRoundedBoxBrush>(FLinearColor::White, 256.f); }
	virtual FVector2D ComputeDesiredSize(float) const override { return FVector2D(8, 8); }
	virtual int32 OnPaint(const FPaintArgs&, const FGeometry& G, const FSlateRect&, FSlateWindowElementList& Out, int32 Layer, const FWidgetStyle&, bool) const override
	{
		if (!M.IsValid() || M->PageInk <= .001f) return Layer;
		const FVector2f Sz = FVector2f(G.GetLocalSize()); const float T = FMath::Clamp(M->PageInk, 0.f, 1.f);
		FRandomStream R(M->PageSeed);
		const FLinearColor Ink(.035f, .025f, .03f, 1.f);
		const int32 N = 46;
		for (int32 i = 0; i < N; i++)
		{
			// blobs sit on a jittered grid and toward the edges; inner ones dry first
			const FVector2f C(R.FRandRange(-.05f, 1.05f) * Sz.X, R.FRandRange(-.05f, 1.05f) * Sz.Y);
			const float Edge = FMath::Min(FMath::Min(C.X, Sz.X - C.X) / Sz.X, FMath::Min(C.Y, Sz.Y - C.Y) / Sz.Y);   // 0 at the border
			const float Prog = 1.f - T;                                                        // 0 → 1 over the reveal
			const float Start = FMath::Clamp((.5f - Edge) * .9f, 0.f, .45f) * 0.f + FMath::Clamp(Edge, 0.f, .5f) * .9f + R.FRandRange(0.f, .12f);   // centre dries first, edges last
			const float K = 1.f - FMath::Clamp((Prog - Start) / FMath::Max(.15f, .95f - Start), 0.f, 1.f);
			const float Rad = Sz.GetMax() * R.FRandRange(.16f, .3f) * FMath::Pow(K, .7f);
			if (Rad < 2.f) continue;
			const FVector2f Ext(Rad * R.FRandRange(1.f, 1.5f), Rad * R.FRandRange(.8f, 1.2f));
			FSlateDrawElement::MakeBox(Out, Layer, G.ToPaintGeometry(Ext * 2.f, FSlateLayoutTransform(C - Ext)), Dot.Get(), ESlateDrawEffect::None, Ink);
			if (i % 5 == 0)   // a drip running down from the blob
			{
				const FVector2f DExt(Rad * .08f, Rad * R.FRandRange(.6f, 1.2f));
				FSlateDrawElement::MakeBox(Out, Layer, G.ToPaintGeometry(DExt * 2.f, FSlateLayoutTransform(C + FVector2f(R.FRandRange(-.4f, .4f) * Rad, 0.f) - FVector2f(DExt.X, 0.f))), Dot.Get(), ESlateDrawEffect::None, Ink);
			}
		}
		return Layer + 1;
	}
private:
	TSharedPtr<FPBXUIModel> M; TSharedPtr<FSlateBrush> Dot;
};

class SPBXMarks : public SLeafWidget
{
public:
	SLATE_BEGIN_ARGS(SPBXMarks) {}
	SLATE_END_ARGS()
	void Construct(const FArguments&, TSharedPtr<FPBXUIModel> InM) { M = InM; Dot = MakeShared<FSlateRoundedBoxBrush>(FLinearColor::White, 64.f); }
	virtual FVector2D ComputeDesiredSize(float) const override { return FVector2D(8, 8); }
	virtual int32 OnPaint(const FPaintArgs&, const FGeometry& G, const FSlateRect&, FSlateWindowElementList& Out, int32 Layer, const FWidgetStyle&, bool) const override
	{
		if (!M.IsValid() || M->Mode != EPBXUIMode::Explore) return Layer;
		for (const FPBXUIModel::FMark& K : M->Marks)
		{
			if (K.A <= .01f) continue;
			const float Pulse = .5f + .5f * FMath::Sin(M->Time * 2.2f + K.P.X * .01f);
			const float R = (K.bEdge ? 9.f : 11.f) + Pulse * 3.f;
			FLinearColor Halo(1.f, .78f, .42f, K.A * (.18f + .12f * Pulse)), Core(1.f, .9f, .7f, K.A * .85f), Ring(.08f, .05f, .04f, K.A * .7f);
			auto Box = [&](float Sz, const FLinearColor& C, int32 L) { FSlateDrawElement::MakeBox(Out, L, G.ToPaintGeometry(FVector2f(Sz, Sz), FSlateLayoutTransform(FVector2f(K.P) - FVector2f(Sz, Sz) * .5f)), Dot.Get(), ESlateDrawEffect::None, C); };
			Box(R * 3.2f, Halo, Layer); Box(R * 1.15f, Ring, Layer + 1); Box(R * .8f, Core, Layer + 2);
		}
		return Layer + 2;
	}
private:
	TSharedPtr<FPBXUIModel> M; TSharedPtr<FSlateBrush> Dot;
};

TSharedRef<SWidget> SPBXHud::Panel(TSharedRef<SWidget> Content, FLinearColor Fill, float Pad)
{
	// light fills = a parchment page (ink text), dark fills = an ink-wash strip (ivory text). Small panels use a smaller
	// 9-slice so the ruled frame never touches the text.
	const bool bLight = Fill.R + Fill.G + Fill.B > 1.5f;
	return SNew(SBorder).BorderImage(bLight ? Parchment() : InkWash()).Padding(FMargin(FMath::Max(Pad + 16.f, 30.f), FMath::Max(Pad + 12.f, 26.f)))[Content];
}

/** shear (x by y) + scale + translation as one Slate render transform */
static FSlateRenderTransform XForm(float Shear, float Sx, float Sy, FVector2D T = FVector2D::ZeroVector)
{
	return FSlateRenderTransform(FMatrix2x2(Sx, 0.f, Shear, Sy), FVector2f(T));
}

static EVisibility Vis(bool b) { return b ? EVisibility::SelfHitTestInvisible : EVisibility::Collapsed; }

void SPBXHud::Construct(const FArguments& Args, TSharedPtr<FPBXUIModel> InModel)
{
	M = InModel; Sink = &Keep;
	ForceVolatile(true);
	TSharedPtr<FSlateBrush> TagB;   // (old dark speaker tab: now a crimson brush ribbon)
	TSharedPtr<FSlateBrush> Dark = MakeShared<FSlateColorBrush>(FLinearColor(0, 0, 0, .55f)); Keep.Add(Dark);
	(void)TagB;

	TSharedRef<SCanvas> Canvas = SNew(SCanvas);
	for (int32 i = 0; i < 8; i++)
	{
		Canvas->AddSlot().Position_Lambda([this, i] { return M->Floaters[i].Screen; }).Size(FVector2D(360, 90)).HAlign(HAlign_Center).VAlign(VAlign_Center)
		[
			SNew(STextBlock).Text_Lambda([this, i] { return FText::FromString(M->Floaters[i].T < 1.2f ? M->Floaters[i].Text : FString()); })
			.Font(PBXUI::Font(TEXT("title"), 58, 4)).ColorAndOpacity_Lambda([this, i] { FLinearColor C = M->Floaters[i].Color; C.A = FMath::Clamp(1.2f - M->Floaters[i].T, 0.f, 1.f) * 2.f; return FSlateColor(C); })
			.RenderTransform_Lambda([this, i] { const FPBXFloater& F = M->Floaters[i]; const float Pop = F.T < .15f ? F.T / .15f * 1.35f : FMath::Lerp(1.35f, 1.f, FMath::Min(1.f, (F.T - .15f) * 5.f));
				return XForm(0.f, F.Scale * .6f * Pop, F.Scale * .6f * Pop, FVector2D(0, -F.T * 70.f)); }).RenderTransformPivot(FVector2D(.5f, .5f))
		];
	}

	ChildSlot
	[
		SNew(SOverlay).Visibility(EVisibility::SelfHitTestInvisible)

		// ---------------- explore HUD: objective (top-left)
		+ SOverlay::Slot().HAlign(HAlign_Left).VAlign(VAlign_Top).Padding(28, 24)
		[
			SNew(SBox).WidthOverride(560).Visibility_Lambda([this] { return Vis(M->Mode == EPBXUIMode::Explore && !M->Objective.IsEmpty() && M->BigT <= 0.f && M->Letterbox < .05f); })
			[
				Panel(SNew(SVerticalBox)
					+ SVerticalBox::Slot().AutoHeight()[SNew(STextBlock).Text_Lambda([this] { return FText::FromString(M->Chapter.ToUpper()); }).Font(PBXUI::Font(TEXT("label"), 14)).ColorAndOpacity(CrimsonC)]
					+ SVerticalBox::Slot().AutoHeight().Padding(0, 2, 0, 0)
					[
						SNew(SHorizontalBox)
						+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0, 0, 10, 0)
						[
							SNew(STextBlock).Text(FText::FromString(TEXT(">"))).Font(PBXUI::Font(TEXT("title"), 30)).ColorAndOpacity(CrimsonC)
							.Visibility_Lambda([this] { return M->bArrow ? EVisibility::HitTestInvisible : EVisibility::Hidden; })
							.RenderTransform_Lambda([this] { return FSlateRenderTransform(FQuat2D(FMath::DegreesToRadians(M->ArrowAngle))); }).RenderTransformPivot(FVector2D(.5f, .5f))
						]
						+ SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)[SNew(STextBlock).Text_Lambda([this] { return FText::FromString(M->Objective); }).Font(PBXUI::Font(TEXT("bold"), 26)).ColorAndOpacity(TextC).AutoWrapText(true)]
						+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(10, 0, 0, 0)[SNew(STextBlock).Text_Lambda([this] { return FText::FromString(M->Distance >= 0 ? FString::Printf(TEXT("%d m"), M->Distance) : FString()); }).Font(PBXUI::Font(TEXT("italic"), 22)).ColorAndOpacity(CrimsonC)]
					], PaperC, 14.f)
			]
		]

		// ---------------- partner plate (bottom-left)
		+ SOverlay::Slot().HAlign(HAlign_Left).VAlign(VAlign_Bottom).Padding(28, 24)
		[
			SNew(SBox).WidthOverride(330).Visibility_Lambda([this] { return Vis(M->Mode == EPBXUIMode::Explore && M->Partner.bShow); })
			[
				Panel(SNew(SVerticalBox)
					+ SVerticalBox::Slot().AutoHeight()
					[
						SNew(SHorizontalBox)
						+ SHorizontalBox::Slot().FillWidth(1)[SNew(STextBlock).Text_Lambda([this] { return FText::FromString(M->Partner.Name); }).Font(PBXUI::Font(TEXT("title"), 22)).ColorAndOpacity(TextC)]
						+ SHorizontalBox::Slot().AutoWidth()[SNew(STextBlock).Text_Lambda([this] { return FText::FromString(FString::Printf(TEXT("Lv %d"), M->Partner.Lv)); }).Font(PBXUI::Font(TEXT("italic"), 21)).ColorAndOpacity(CrimsonC)]
					]
					+ SVerticalBox::Slot().AutoHeight().Padding(0, 6, 0, 0)
					[
						SNew(SOverlay)
						+ SOverlay::Slot()[SNew(SBox).HeightOverride(16).WidthOverride(262)[SNew(SImage).Image(StrokeBox()).ColorAndOpacity(FLinearColor(.25f, .17f, .1f, .22f))]]
						+ SOverlay::Slot().HAlign(HAlign_Left)[SNew(SBox).HeightOverride(16).WidthOverride_Lambda([this] { return FOptionalSize(262.f * FMath::Clamp(float(M->Partner.HP) / FMath::Max(1, M->Partner.MaxHP), 0.f, 1.f)); })
							[SNew(SImage).Image(StrokeBox()).ColorAndOpacity_Lambda([this] { const float k = float(M->Partner.HP) / FMath::Max(1, M->Partner.MaxHP); return FSlateColor(k > .5f ? FLinearColor(.16f, .36f, .18f) : k > .2f ? FLinearColor(.66f, .45f, .1f) : CrimsonC); })]]
					], PaperC, 12.f)
			]
		]

		// ---------------- interaction prompt (bottom-center)
		+ SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Bottom).Padding(0, 0, 0, 120)
		[
			SNew(SBox).Visibility_Lambda([this] { return Vis(M->Mode == EPBXUIMode::Explore && !M->Prompt.IsEmpty()); })
			[
				Panel(SNew(STextBlock).Text_Lambda([this] { return FText::FromString(M->Prompt); }).Font(PBXUI::Font(TEXT("bold"), 26)).ColorAndOpacity(TextC), PaperC, 12.f)
			]
		]

		// ---------------- toasts (top-right)
		+ SOverlay::Slot().HAlign(HAlign_Right).VAlign(VAlign_Top).Padding(28, 24)
		[
			SNew(SVerticalBox)
			+ SVerticalBox::Slot().AutoHeight()[SNew(SBox).WidthOverride(430).Visibility_Lambda([this] { return Vis(M->Toasts.Num() > 0); })
				[Panel(SNew(STextBlock).Text_Lambda([this] { return FText::FromString(M->Toasts.Num() ? M->Toasts[0].Text : FString()); }).Font(PBXUI::Font(TEXT("bold"), 22)).ColorAndOpacity(TextC).AutoWrapText(true), FLinearColor(1, .95f, .75f), 12.f)]]
			+ SVerticalBox::Slot().AutoHeight().Padding(0, 8, 0, 0)[SNew(SBox).WidthOverride(430).Visibility_Lambda([this] { return Vis(M->Toasts.Num() > 1); })
				[Panel(SNew(STextBlock).Text_Lambda([this] { return FText::FromString(M->Toasts.Num() > 1 ? M->Toasts[1].Text : FString()); }).Font(PBXUI::Font(TEXT("bold"), 22)).ColorAndOpacity(TextC).AutoWrapText(true), FLinearColor(1, .95f, .75f), 12.f)]]
		]

		// ---------------- battle layer
		+ SOverlay::Slot()
		[
			SNew(SOverlay).Visibility_Lambda([this] { return M->Mode == EPBXUIMode::Battle ? EVisibility::SelfHitTestInvisible : EVisibility::Collapsed; })
			.RenderTransform_Lambda([this] { const float s = M->ShakeT > 0.f ? 14.f * M->ShakeT : 0.f; return FSlateRenderTransform(FVector2D(FMath::Sin(M->ShakeT * 90.f) * s, FMath::Cos(M->ShakeT * 70.f) * s)); })
			// letterbox bars: cinematic frame while the battle runs
			+ SOverlay::Slot().VAlign(VAlign_Top)[SNew(SBox).HeightOverride(54)[SNew(SImage).Image(White()).ColorAndOpacity(FLinearColor(0, 0, 0, .85f))]]
			+ SOverlay::Slot().VAlign(VAlign_Bottom)[SNew(SBox).HeightOverride(54)[SNew(SImage).Image(White()).ColorAndOpacity(FLinearColor(0, 0, 0, .85f))]]
			// Gen 1-3 layout: each HP plate sits opposite its creature -> foe (upper right) plate top-left, yours (lower left) on the right above the moves
			+ SOverlay::Slot().HAlign(HAlign_Left).VAlign(VAlign_Top).Padding(48, 78)[MakePlate(1)]
			+ SOverlay::Slot().HAlign(HAlign_Right).VAlign(VAlign_Bottom).Padding(48, 0, 48, 490)[MakePlate(0)]   // above the move cards (up to 4 rows)
			// battle log: slim dark strip under the top bar
			+ SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Top).Padding(0, 66)
			[
				SNew(SBox).WidthOverride(820).Visibility_Lambda([this] { return Vis(!M->Log.IsEmpty() && M->IntroT <= 0.f && M->BannerT <= 0.f); })
				[
					SNew(SBorder).BorderImage(InkWash()).Padding(FMargin(40, 16))
					[SNew(STextBlock).Text_Lambda([this] { return FText::FromString(M->Log); }).Font(PBXUI::Font(TEXT("body"), 29)).ColorAndOpacity(IvoryC).AutoWrapText(true).Justification(ETextJustify::Center)]
				]
			]
			+ SOverlay::Slot().HAlign(HAlign_Right).VAlign(VAlign_Bottom).Padding(48, 78)
			[
				SAssignNew(MovesHost, SBox).WidthOverride(780).Visibility_Lambda([this] { return M->bMoves ? EVisibility::Visible : EVisibility::Collapsed; })
				.RenderTransform_Lambda([this] { const float k = FMath::Clamp(M->MovesIn, 0.f, 1.f); return FSlateRenderTransform(FVector2D((1.f - FMath::Sin(k * PI * .5f)) * 760.f, 0)); })
			]
			// banner: slanted colour strip that pops in (wild appeared / super effective / critical)
			+ SOverlay::Slot().HAlign(HAlign_Fill).VAlign(VAlign_Center).Padding(FMargin(0, 120, 0, 0))   // between the foe and your Echo, clear of the plates
			[
				SNew(SBorder).BorderImage(Stroke()).BorderBackgroundColor_Lambda([this] { FLinearColor C = M->BannerColor * .8f; C.A = 1.f; return FSlateColor(C); }).Padding(FMargin(0, 26)).HAlign(HAlign_Center)
				.Visibility_Lambda([this] { return Vis(M->BannerT > 0.f && !M->Banner.IsEmpty()); })
				.RenderTransform_Lambda([this] { const float In = FMath::Clamp((M->BannerMax - M->BannerT) * 6.f, 0.f, 1.f); const float Out = FMath::Clamp(M->BannerT * 5.f, 0.f, 1.f);
					return XForm(-.06f, 1.f, FMath::Max(.001f, In * Out)); }).RenderTransformPivot(FVector2D(.5f, .5f))
				[SNew(STextBlock).Text_Lambda([this] { return FText::FromString(M->Banner.ToUpper()); }).Font(PBXUI::Font(TEXT("title"), 72, 4)).ColorAndOpacity(IvoryC)
					.RenderTransform_Lambda([this] { const float In = FMath::Clamp((M->BannerMax - M->BannerT) * 4.f, 0.f, 1.f); return FSlateRenderTransform(FVector2D((1.f - In) * -900.f, 0)); })]
			]
			// VS intro: two team-coloured bars slam in from the sides, VS pops in the middle
			+ SOverlay::Slot()
			[
				SNew(SOverlay).Visibility_Lambda([this] { return Vis(M->IntroT > 0.f); })
				+ SOverlay::Slot().VAlign(VAlign_Center).HAlign(HAlign_Left).Padding(0, 0, 0, 170)
				[
					SNew(SBox).WidthOverride_Lambda([this] { return FOptionalSize(M->ViewSize.X * .62f); }).HeightOverride(150)
					.RenderTransform_Lambda([this] { const float k = FMath::Clamp((1.9f - M->IntroT) * 4.f, 0.f, 1.f) * FMath::Clamp(M->IntroT * 4.f, 0.f, 1.f); return XForm(-.25f, 1.f, 1.f, FVector2D((k - 1.f) * M->ViewSize.X * .7f, 0)); })
					[
						SNew(SBorder).BorderImage(Stroke()).BorderBackgroundColor_Lambda([this] { return FSlateColor(M->IntroColA * .75f); }).HAlign(HAlign_Center).VAlign(VAlign_Center)
						[SNew(STextBlock).Text_Lambda([this] { return FText::FromString(M->IntroA.ToUpper()); }).Font(PBXUI::Font(TEXT("title"), 76, 4)).ColorAndOpacity(IvoryC)]
					]
				]
				+ SOverlay::Slot().VAlign(VAlign_Center).HAlign(HAlign_Right).Padding(0, 170, 0, 0)
				[
					SNew(SBox).WidthOverride_Lambda([this] { return FOptionalSize(M->ViewSize.X * .62f); }).HeightOverride(150)
					.RenderTransform_Lambda([this] { const float k = FMath::Clamp((1.75f - M->IntroT) * 4.f, 0.f, 1.f) * FMath::Clamp(M->IntroT * 4.f, 0.f, 1.f); return XForm(-.25f, 1.f, 1.f, FVector2D((1.f - k) * M->ViewSize.X * .7f, 0)); })
					[
						SNew(SBorder).BorderImage(Stroke()).BorderBackgroundColor_Lambda([this] { return FSlateColor(M->IntroColB * .75f); }).HAlign(HAlign_Center).VAlign(VAlign_Center)
						[SNew(STextBlock).Text_Lambda([this] { return FText::FromString(M->IntroB.ToUpper()); }).Font(PBXUI::Font(TEXT("title"), 76, 4)).ColorAndOpacity(IvoryC)]
					]
				]
				+ SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Center)
				[
					SNew(STextBlock).Text(FText::FromString(TEXT("VS"))).Font(PBXUI::Font(TEXT("title"), 170, 8)).ColorAndOpacity(FLinearColor(.78f, .09f, .06f))
					.RenderTransform_Lambda([this] { const float t = 1.9f - M->IntroT; const float k = t < .45f ? 0.f : FMath::Min(1.f, (t - .45f) * 5.f); const float s = k * (1.f + .35f * FMath::Sin(FMath::Min(1.f, (t - .45f) * 3.f) * PI)); return XForm(0.f, FMath::Max(.001f, s), FMath::Max(.001f, s)); })
					.RenderTransformPivot(FVector2D(.5f, .5f))
				]
			]
			+ SOverlay::Slot()[Canvas]
		]

		// ---------------- dialogue (bottom)
		+ SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Bottom).Padding(0, 0, 0, 46)
		[
			SNew(SBox).WidthOverride(1180).Visibility_Lambda([this] { return M->Mode == EPBXUIMode::Dialogue ? EVisibility::Visible : EVisibility::Collapsed; })
			[
				SNew(SOverlay)
				+ SOverlay::Slot().Padding(0, 30, 0, 0)
				[
					Panel(SNew(SBox).MinDesiredHeight(130)
						[
							SNew(SVerticalBox)
							+ SVerticalBox::Slot().FillHeight(1).Padding(8, 14, 8, 0)[SNew(STextBlock).Text_Lambda([this] { return FText::FromString(M->Line.Left(FMath::FloorToInt(M->Visible))); }).Font(PBXUI::Font(TEXT("body"), 33)).ColorAndOpacity(TextC).AutoWrapText(true)]
							+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Right)[SNew(STextBlock).Text(FText::FromString(TEXT("E / click  >"))).Font(PBXUI::Font(TEXT("italic"), 19)).ColorAndOpacity(SepiaC)
								.Visibility_Lambda([this] { return M->Visible >= M->Line.Len() ? EVisibility::HitTestInvisible : EVisibility::Hidden; })]
						], PaperC, 22.f)
				]
				+ SOverlay::Slot().HAlign(HAlign_Left).VAlign(VAlign_Top).Padding(30, 0, 0, 0)
				[
					SNew(SBorder).BorderImage(Stroke()).BorderBackgroundColor(CrimsonC).Padding(FMargin(34, 10, 54, 10)).Visibility_Lambda([this] { return Vis(!M->Speaker.IsEmpty()); })
					[SNew(STextBlock).Text_Lambda([this] { return FText::FromString(M->Speaker.ToUpper()); }).Font(PBXUI::Font(TEXT("title"), 26)).ColorAndOpacity(IvoryC)]
				]
			]
		]

		// ---------------- the title screen's drawn background loop (under the menus)
		+ SOverlay::Slot()
		[
			SNew(SBorder).BorderImage(White()).BorderBackgroundColor(FLinearColor::Black).Padding(0)
			.Visibility_Lambda([this] { return M->MovieBgA > .001f && M->MovieBrush.IsValid() && M->MovieA <= .001f ? EVisibility::HitTestInvisible : EVisibility::Collapsed; })
			[
				SNew(SScaleBox).Stretch(EStretch::ScaleToFill)
				[ SNew(SImage).Image_Lambda([this] { return M->MovieBrush.Get(); }).ColorAndOpacity_Lambda([this] { return FSlateColor(FLinearColor(1, 1, 1, M->MovieBgA)); }) ]
			]
		]
		// ---------------- choice / menus (center): an ink vignette darkens the world behind the page
		+ SOverlay::Slot()
		[
			SNew(SImage).Image(Codex(TEXT("ui_vignette"), FVector2f(960.f, 540.f))).ColorAndOpacity_Lambda([this] { return FSlateColor(FLinearColor(1, 1, 1, M->bMenuLeft ? .35f : M->bStoryChoice ? .45f : .7f)); }).Visibility_Lambda([this] { return (M->Mode == EPBXUIMode::Choice || M->Mode == EPBXUIMode::Menu) ? EVisibility::HitTestInvisible : EVisibility::Collapsed; })
		]
		+ SOverlay::Slot().Padding(0, 24)   // r67: scaled down to fit when a list is taller than the screen (Your Codex, long story choices)
		[
			SNew(SScaleBox).Stretch(EStretch::ScaleToFit).StretchDirection(EStretchDirection::DownOnly).HAlign(HAlign_Center).VAlign(VAlign_Center)
			[
			SNew(SVerticalBox).Visibility_Lambda([this] { return (M->Mode == EPBXUIMode::Choice || M->Mode == EPBXUIMode::Menu) ? EVisibility::Visible : EVisibility::Collapsed; })
			.RenderTransform_Lambda([this] { return FSlateRenderTransform(FVector2D(M->bMenuLeft ? -M->ViewSize.X * .24f : 0.f, M->bStoryChoice ? M->ViewSize.Y * .06f : 0.f)); })
			+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center)[SNew(STextBlock).Text_Lambda([this] { return FText::FromString(M->ChoiceTitle); }).Font(PBXUI::Font(TEXT("title"), 68, 4)).ColorAndOpacity(IvoryC)]
			+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center).Padding(0, 0, 0, 22)[SNew(STextBlock).Text_Lambda([this] { return FText::FromString(M->ChoiceSub); }).Font(PBXUI::Font(TEXT("italic"), 28, 2)).ColorAndOpacity(IvoryC).Justification(ETextJustify::Center)]
			+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center)[SAssignNew(ChoiceHost, SBox)]
			// v3: the burning fuse of a timed story choice (ink that burns down from both ends; silence is a choice too)
			+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center).Padding(0, 14, 0, 0)
			[
				SNew(SBox).HeightOverride(14).WidthOverride_Lambda([this] { return FOptionalSize(600.f * FMath::Clamp(M->FuseMax > 0.f ? M->FuseT / M->FuseMax : 0.f, 0.f, 1.f)); })
				.Visibility_Lambda([this] { return M->FuseMax > 0.f ? EVisibility::HitTestInvisible : EVisibility::Collapsed; })
				[
					SNew(SImage).Image(StrokeBox()).ColorAndOpacity_Lambda([this] { const float k = M->FuseMax > 0.f ? M->FuseT / M->FuseMax : 0.f;
						FLinearColor C = FLinearColor::LerpUsingHSV(FLinearColor(.85f, .12f, .08f), FLinearColor(1.f, .7f, .3f), k);
						if (k < .3f) C *= 1.f + .5f * FMath::Abs(FMath::Sin(M->Time * 10.f)); return FSlateColor(C); })
				]
			]
			]
		]

		// ---------------- big splash (chapter, captured, complete)
		+ SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Center).Padding(0, 0, 0, 420)   // high enough to clear faces
		[
			SNew(SVerticalBox).Visibility_Lambda([this] { return Vis(M->BigT > 0.f && !M->BigTitle.IsEmpty()); })
			+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center)[SNew(STextBlock).Text_Lambda([this] { return FText::FromString(M->BigTitle); }).Font(PBXUI::Font(TEXT("title"), 88, 5))
				.ColorAndOpacity_Lambda([this] { FLinearColor C = GoldC; C.A = FMath::Clamp(M->BigT, 0.f, 1.f); return FSlateColor(C); })]
			+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center)[SNew(STextBlock).Text_Lambda([this] { return FText::FromString(M->BigSub); }).Font(PBXUI::Font(TEXT("italic"), 34, 3))
				.ColorAndOpacity_Lambda([this] { return FSlateColor(FLinearColor(1, 1, 1, FMath::Clamp(M->BigT, 0.f, 1.f))); })]
		]

		// ---------------- the saga intro video (full screen, scaled to fill, black behind)
		+ SOverlay::Slot()
		[
			SNew(SBorder).BorderImage(White()).BorderBackgroundColor(FLinearColor::Black).Padding(0)
			.Visibility_Lambda([this] { return M->MovieA > .001f && M->MovieBrush.IsValid() ? EVisibility::HitTestInvisible : EVisibility::Collapsed; })
			[
				SNew(SScaleBox).Stretch(EStretch::ScaleToFit)
				[ SNew(SImage).Image_Lambda([this] { return M->MovieBrush.Get(); }).ColorAndOpacity_Lambda([this] { return FSlateColor(FLinearColor(1, 1, 1, M->MovieA)); }) ]
			]
		]
		// ---------------- intro "ink myth" overlay (Sigil & Spark)
		+ SOverlay::Slot()[ SNew(SPBXMarks, M).Visibility(EVisibility::HitTestInvisible) ]
		+ SOverlay::Slot()[ SNew(SPBXInk, M).Visibility(EVisibility::HitTestInvisible) ]
		// ---------------- cutscene letterbox + caption (phase 6)
		+ SOverlay::Slot().VAlign(VAlign_Top)
		[
			SNew(SBox).Visibility(EVisibility::HitTestInvisible).HeightOverride_Lambda([this] { return FOptionalSize(M->ViewSize.Y * .11f * M->Letterbox); })[SNew(SImage).Image(White()).ColorAndOpacity(FLinearColor(0, 0, 0, 1))]
		]
		+ SOverlay::Slot().VAlign(VAlign_Bottom)
		[
			SNew(SBox).Visibility(EVisibility::HitTestInvisible).HeightOverride_Lambda([this] { return FOptionalSize(M->ViewSize.Y * .11f * M->Letterbox); })[SNew(SImage).Image(White()).ColorAndOpacity(FLinearColor(0, 0, 0, 1))]
		]
		+ SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Bottom).Padding(0, 0, 0, 150)
		[
			SNew(SVerticalBox).Visibility_Lambda([this] { return M->CaptionA > 0.f ? EVisibility::HitTestInvisible : EVisibility::Collapsed; })
			+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center)[SNew(STextBlock).Text_Lambda([this] { return FText::FromString(M->Caption); }).Font(PBXUI::Font(TEXT("title"), 64, 3))
				.ColorAndOpacity_Lambda([this] { return FSlateColor(FLinearColor(1, .96f, .88f, M->CaptionA)); })]
			+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center).Padding(0, 6, 0, 0)[SNew(STextBlock).Text_Lambda([this] { return FText::FromString(M->CaptionSub); }).Font(PBXUI::Font(TEXT("body"), 26, 2))
				.ColorAndOpacity_Lambda([this] { return FSlateColor(FLinearColor(1, 1, 1, .9f * M->CaptionA)); })]
		]
		// ---------------- subtitles (user 2026-10-31: every narrated / spoken line of the intro)
		+ SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Bottom).Padding(0, 0, 0, 34)
		[
			SNew(SBorder).Visibility_Lambda([this] { return M->bSubtitles && M->SubA > .01f && !M->Subtitle.IsEmpty() ? EVisibility::HitTestInvisible : EVisibility::Collapsed; })
			.BorderImage(InkWash()).BorderBackgroundColor_Lambda([this] { return FSlateColor(FLinearColor(1, 1, 1, .85f * M->SubA)); }).Padding(FMargin(40, 14))
			[
				SNew(STextBlock).Text_Lambda([this] { return FText::FromString(M->SubSpeaker.IsEmpty() ? M->Subtitle : M->SubSpeaker + TEXT(":  ") + M->Subtitle); })
				.Font(PBXUI::Font(TEXT("body"), 28)).Justification(ETextJustify::Center).WrapTextAt(1150.f)   // fixed width: AutoWrapText collapsed the bar to 3-5 short lines (r61)
				.ColorAndOpacity_Lambda([this] { return FSlateColor(FLinearColor(1, 1, 1, M->SubA)); })
			]
		]
		+ SOverlay::Slot().HAlign(HAlign_Right).VAlign(VAlign_Bottom).Padding(0, 0, 40, 30)
		[
			SNew(STextBlock).Visibility_Lambda([this] { return M->Letterbox > .9f ? EVisibility::HitTestInvisible : EVisibility::Collapsed; })
			.Text(FText::FromString(TEXT("E  skip"))).Font(PBXUI::Font(TEXT("italic"), 20)).ColorAndOpacity(FLinearColor(1, 1, 1, .55f))
		]

		// ---------------- full-screen flash (big hits, the White Page's light)
		+ SOverlay::Slot()
		[
			SNew(SImage).Image(White()).Visibility(EVisibility::HitTestInvisible).ColorAndOpacity_Lambda([this] { FLinearColor C = M->FlashColor; C.A = FMath::Clamp(M->FlashT, 0.f, 1.f) * .85f; return FSlateColor(C); })
		]
		// ---------------- fade
		+ SOverlay::Slot()
		[
			SNew(SImage).Image(White()).Visibility(EVisibility::HitTestInvisible).ColorAndOpacity_Lambda([this] { return FSlateColor(FLinearColor(0, 0, 0, M->Fade)); })
		]
		// ---------------- scene change: ink blots drawing back to reveal the page
		+ SOverlay::Slot()
		[
			SNew(SPBXPageInk, M).Visibility(EVisibility::HitTestInvisible)
		]
		// ---------------- prologue cards (over the fade: white words on black)
		+ SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Center)
		[
			SNew(SVerticalBox).Visibility_Lambda([this] { return M->CardA > .01f ? EVisibility::HitTestInvisible : EVisibility::Collapsed; })
			+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center)[SNew(STextBlock).Text_Lambda([this] { return FText::FromString(M->CardText); }).Font(PBXUI::Font(TEXT("body"), 40)).Justification(ETextJustify::Center).WrapTextAt(1200.f)
				.ColorAndOpacity_Lambda([this] { return FSlateColor(FLinearColor(1.f, .96f, .9f, M->CardA)); })]
			+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center).Padding(0, 22, 0, 0)[SNew(STextBlock).Text_Lambda([this] { return FText::FromString(M->CardSub); }).Font(PBXUI::Font(TEXT("italic"), 28)).Justification(ETextJustify::Center).WrapTextAt(1100.f)
				.ColorAndOpacity_Lambda([this] { return FSlateColor(FLinearColor(.85f, .25f, .2f, M->CardA)); })]
		]
	];
}

TSharedRef<SWidget> SPBXHud::MakePlate(int32 Side)
{
	auto P = [this, Side]() -> FPBXPlate& { return M->Plate[Side]; };
	// a parchment card: name in Roman capitals, the Ink type as a wax-sealed tag, HP as a brush stroke, energy as seals
	const FSlateBrush* Bg = Parchment(false, 220.f);
	TSharedPtr<FSlateBrush> Badge = MakeShared<FSlateRoundedBoxBrush>(FLinearColor::White, 4.f); Sink->Add(Badge);
	const FSlateBrush* Bar = StrokeBox();
	const FSlateBrush* Pip = Seal();
	const float W = 420.f;
	TSharedRef<SHorizontalBox> Pips = SNew(SHorizontalBox);
	for (int32 i = 0; i < 5; i++)
		Pips->AddSlot().AutoWidth().Padding(3, 0)
		[
			SNew(SBox).WidthOverride(18).HeightOverride(18)
			[
				SNew(SImage).Image(Pip).ColorAndOpacity_Lambda([this, P, i]
				{
					const bool bOn = i < P().Energy; FLinearColor C = PBXData::TypeColor(P().Type);
					if (!bOn) return FSlateColor(FLinearColor(.55f, .47f, .36f, .35f));   // an empty seal: a faint impression
					const float Glow = 1.f + .35f * FMath::Sin(M->Time * 6.f + i);   // charged pips shimmer
					return FSlateColor(FLinearColor(C.R * Glow, C.G * Glow, C.B * Glow, 1.f));
				})
			]
		];
	return SNew(SBox).WidthOverride(W).Visibility_Lambda([this, Side] { return Vis(M->Plate[Side].bShow); })
		// slides in from its screen edge after the VS intro
		.RenderTransform_Lambda([this, Side] { const float k = M->IntroT > 0.f ? 0.f : 1.f; (void)k; const float In = FMath::Clamp(1.f - M->IntroT * 2.f, 0.f, 1.f); return XForm(0.f, 1.f, 1.f, FVector2D((1.f - In) * (Side == 0 ? -520.f : 520.f), 0)); })
	[
		SNew(SBorder).BorderImage(Bg).Padding(FMargin(32, 26))
		[
			SNew(SVerticalBox)
			+ SVerticalBox::Slot().AutoHeight()
			[
				SNew(SHorizontalBox)
				+ SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)[SNew(STextBlock).Text_Lambda([P] { return FText::FromString(P().Name.ToUpper()); }).Font(PBXUI::Font(TEXT("title"), 30)).ColorAndOpacity(TextC)]
				+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(8, 0)
				[
					SNew(SBorder).BorderImage(Badge.Get()).BorderBackgroundColor_Lambda([P] { return FSlateColor(PBXData::TypeColor(P().Type) * .7f); }).Padding(FMargin(10, 1))
					[SNew(STextBlock).Text_Lambda([P] { return FText::FromString(PBXData::InkName(P().Type).ToUpper()); }).Font(PBXUI::Font(TEXT("label"), 14)).ColorAndOpacity(IvoryC)]
				]
				+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[SNew(STextBlock).Text_Lambda([P] { return FText::FromString(FString::Printf(TEXT("Lv %d"), P().Lv)); }).Font(PBXUI::Font(TEXT("italic"), 26)).ColorAndOpacity(CrimsonC)]
			]
			+ SVerticalBox::Slot().AutoHeight().Padding(0, 6, 0, 0)
			[
				SNew(SOverlay)
				+ SOverlay::Slot()[SNew(SBox).HeightOverride(24).WidthOverride(W - 68)[SNew(SImage).Image(Bar).ColorAndOpacity(FLinearColor(.25f, .17f, .1f, .22f))]]
				// damage trail (white, catches up with the real HP)
				+ SOverlay::Slot().HAlign(HAlign_Left)[SNew(SBox).HeightOverride(24).WidthOverride_Lambda([P, W] { const float Shown = P().ShownHP < 0.f ? P().HP : P().ShownHP; return FOptionalSize((W - 68) * FMath::Clamp(Shown / FMath::Max(1, P().MaxHP), 0.f, 1.f)); })
					[SNew(SImage).Image(Bar).ColorAndOpacity(FLinearColor(.75f, .35f, .25f, .55f))]]   // damage trail: a pale red wash catching up
				+ SOverlay::Slot().HAlign(HAlign_Left)[SNew(SBox).HeightOverride(24).WidthOverride_Lambda([P, W] { return FOptionalSize((W - 68) * FMath::Clamp(float(FMath::Max(0, P().HP)) / FMath::Max(1, P().MaxHP), 0.f, 1.f)); })
					[SNew(SImage).Image(Bar).ColorAndOpacity_Lambda([this, P] { const float k = float(P().HP) / FMath::Max(1, P().MaxHP);
						FLinearColor C = k > .5f ? FLinearColor(.16f, .36f, .18f) : k > .2f ? FLinearColor(.66f, .45f, .1f) : CrimsonC;
						if (k <= .2f) C *= 1.f + .4f * FMath::Abs(FMath::Sin(M->Time * 8.f));   // low HP blinks
						return FSlateColor(C); })]]
				+ SOverlay::Slot().HAlign(HAlign_Right).VAlign(VAlign_Center).Padding(0, 0, 8, 0)[SNew(STextBlock).Text_Lambda([P] { return FText::FromString(FString::Printf(TEXT("%d / %d"), FMath::Max(0, P().HP), P().MaxHP)); }).Font(PBXUI::Font(TEXT("bold"), 18)).ColorAndOpacity(IvoryC)]
			]
			+ SVerticalBox::Slot().AutoHeight().Padding(0, 8, 0, 0)
			[
				SNew(SHorizontalBox)
				+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0, 0, 6, 0)[SNew(STextBlock).Text(FText::FromString(TEXT("ENERGY"))).Font(PBXUI::Font(TEXT("label"), 13)).ColorAndOpacity(SepiaC)]
				+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[Pips]
				+ SHorizontalBox::Slot().FillWidth(1).HAlign(HAlign_Right).VAlign(VAlign_Center)
				[
					SNew(SBorder).BorderImage(Badge.Get()).BorderBackgroundColor(CrimsonC).Padding(FMargin(8, 1)).Visibility_Lambda([P] { return Vis(!P().Status.IsEmpty()); })
					[SNew(STextBlock).Text_Lambda([P] { return FText::FromString(P().Status.ToUpper()); }).Font(PBXUI::Font(TEXT("label"), 13)).ColorAndOpacity(IvoryC)]
				]
			]
		]
	];
}

TSharedRef<SWidget> SPBXHud::MakeOptions()
{
	TSharedRef<SHorizontalBox> Row = SNew(SHorizontalBox);
	TSharedRef<SVerticalBox> Col = SNew(SVerticalBox);
	const bool bC = !M->bCards && (M->Options.Num() > 5 || M->bStoryChoice);   // story choices: compact rows (3-4 lines must fit under the spoken line)   // long lists (Settings, Pause) use compact rows
	for (int32 i = 0; i < M->Options.Num(); i++)
	{
		const FPBXOption& O = M->Options[i];
		const float Px = M->bCards ? 256.f : 160.f;   // the ruled frame sits at 9 % of Px: keep the text clear of it
		const FSlateBrush* Sel = Parchment(true, Px); const FSlateBrush* Nor = Parchment(false, Px);
		auto OnDown = [this, i](const FGeometry&, const FPointerEvent&) { M->Selected = i; if (M->OnPick && M->Options.IsValidIndex(i) && M->Options[i].bEnabled) M->OnPick(i); return FReply::Handled(); };
		auto Brush = [this, i, Sel, Nor] { return M->Options.IsValidIndex(i) && M->Options[i].bEnabled && M->Selected == i ? Sel : Nor; };
		auto Tint = [this, i] { return FSlateColor(!M->Options.IsValidIndex(i) || !M->Options[i].bEnabled ? FLinearColor(.62f, .58f, .52f, .7f) : M->Selected == i ? FLinearColor::White : FLinearColor(.9f, .87f, .82f, .96f)); };
		TSharedRef<SVerticalBox> Inner = SNew(SVerticalBox);
		if (M->bCards && O.Image.IsValid())
			Inner->AddSlot().AutoHeight().HAlign(HAlign_Center).Padding(0, 0, 0, 10)[SNew(SBox).WidthOverride(180).HeightOverride(252)[SNew(SImage).Image(O.Image.Get())]];
		Inner->AddSlot().AutoHeight().HAlign(M->bCards ? HAlign_Center : HAlign_Left)[SNew(STextBlock).Text(FText::FromString(O.Title)).Font(PBXUI::Font(M->bCards ? TEXT("title") : TEXT("bold"), M->bCards ? 32 : bC ? 25 : 31)).ColorAndOpacity_Lambda([this, i] { return FSlateColor(M->Selected == i ? CrimsonC : TextC); })];
		if (!O.Sub.IsEmpty())
			Inner->AddSlot().AutoHeight().HAlign(M->bCards ? HAlign_Center : HAlign_Left)[SNew(STextBlock).Text(FText::FromString(O.Sub)).Font(PBXUI::Font(TEXT("italic"), 21)).ColorAndOpacity(O.Color.Equals(FLinearColor::White) ? FLinearColor(TextC * .72f) : FLinearColor::LerpUsingHSV(O.Color, SepiaC, .55f)).WrapTextAt(M->bCards ? 230.f : 500.f)];   // fixed width: auto-wrap needs a second layout pass and showed stacked lines on first open   // r67: untinted subs in dark sepia ink (the light wash was unreadable)
		TSharedRef<SWidget> Btn = SNew(SBorder).BorderImage_Lambda(Brush).BorderBackgroundColor_Lambda(Tint).Padding(M->bCards ? FMargin(30, 30) : bC ? FMargin(34, 13) : FMargin(36, 24)).OnMouseButtonDown_Lambda(OnDown)
			.RenderTransform_Lambda([this, i] { return FSlateRenderTransform(M->Selected == i ? 1.03f : 1.f); }).RenderTransformPivot(FVector2D(.5f, .5f))[Inner];
		if (M->bCards) Row->AddSlot().AutoWidth().Padding(14, 0)[SNew(SBox).WidthOverride(260).HeightOverride(390)[Btn]];
		else Col->AddSlot().AutoHeight().Padding(0, bC ? 2 : 5)[SNew(SBox).WidthOverride(600)[Btn]];
	}
	if (M->bCards) return SNew(SBox).WidthOverride(288.f * FMath::Max(1, M->Options.Num())).HeightOverride(390.f)[Row];   // explicit size: the card row came out zero-sized (all three cards drawn on one spot)
	return Col;
}

TSharedRef<SWidget> SPBXHud::MakeMoves()
{
	TSharedRef<SVerticalBox> Col = SNew(SVerticalBox);
	TSharedPtr<SHorizontalBox> Row;
	for (int32 i = 0; i < M->Moves.Num(); i++)
	{
		if (i % 2 == 0) { Row = SNew(SHorizontalBox); Col->AddSlot().AutoHeight().Padding(0, 6)[Row.ToSharedRef()]; }
		const FPBXOption& O = M->Moves[i];
		const FLinearColor Base = O.Color;
		const FSlateBrush* Card = Parchment(false, 160.f); const FSlateBrush* Sel = Parchment(true, 160.f);
		auto Brush = [this, i, Sel, Card] { return M->Moves.IsValidIndex(i) && M->Moves[i].bEnabled && M->MoveSel == i ? Sel : Card; };
		auto Tint = [this, i] { return FSlateColor(!M->Moves.IsValidIndex(i) || !M->Moves[i].bEnabled ? FLinearColor(.6f, .56f, .5f, .75f) : FLinearColor::White); };
		auto OnDown = [this, i](const FGeometry&, const FPointerEvent&) { M->MoveSel = i; if (M->OnMove && M->Moves.IsValidIndex(i) && M->Moves[i].bEnabled) M->OnMove(i); return FReply::Handled(); };
		auto OnHover = [this, i](const FGeometry&, const FPointerEvent&) { M->MoveSel = i; };
		Row->AddSlot().FillWidth(1).Padding(6, 0)
		[
			SNew(SBox).HeightOverride(88)
				.RenderTransform_Lambda([this, i] { const bool bSel = M->MoveSel == i; const float s = bSel ? 1.04f + .012f * FMath::Sin(M->Time * 5.f) : 1.f; return XForm(0.f, s, s); })
			.RenderTransformPivot(FVector2D(.5f, .5f))
			[
				SNew(SBorder).BorderImage_Lambda(Brush).BorderBackgroundColor_Lambda(Tint).Padding(FMargin(26, 15, 26, 12)).OnMouseButtonDown_Lambda(OnDown).OnMouseMove_Lambda([OnHover](const FGeometry& G, const FPointerEvent& E) { OnHover(G, E); return FReply::Unhandled(); })
				[
					SNew(SHorizontalBox)
					+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0, 0, 12, 0)
					[SNew(SBox).WidthOverride(54).HeightOverride(54)[SNew(SBorder).BorderImage(Seal()).BorderBackgroundColor(FLinearColor(Base.R * .75f, Base.G * .75f, Base.B * .75f, 1.f)).HAlign(HAlign_Center).VAlign(VAlign_Center).Padding(0)
							[SNew(STextBlock).Text(FText::FromString(O.Key)).Font(PBXUI::Font(TEXT("title"), 24)).ColorAndOpacity(IvoryC)]]]
					+ SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)
					[
						SNew(SVerticalBox)
						+ SVerticalBox::Slot().AutoHeight()[SNew(STextBlock).Text(FText::FromString(O.Title.ToUpper())).Font(PBXUI::Font(TEXT("title"), 19)).ColorAndOpacity_Lambda([this, i] { return FSlateColor(M->MoveSel == i ? CrimsonC : TextC); })]
							+ SVerticalBox::Slot().AutoHeight()[SNew(STextBlock).Text(FText::FromString(O.Sub)).Font(PBXUI::Font(TEXT("italic"), 17)).ColorAndOpacity(TextC * .75f)]
					]
				]
			]
		];
	}
	return Col;
}

void SPBXHud::Tick(const FGeometry& G, const double Time, const float Dt)
{
	SCompoundWidget::Tick(G, Time, Dt);
	M->ViewSize = FVector2D(G.GetLocalSize()); M->Time += Dt; M->PageInk = FMath::Max(0.f, M->PageInk - Dt / 1.4f);
	PBXUI::TickSparks(*M, Dt);
	M->MovesIn = M->bMoves ? FMath::Min(1.f, M->MovesIn + Dt * 4.f) : 0.f;
	// a list built in the same frame its panel turns visible can lay out stacked (no geometry yet): rebuild it once more a few frames later
	if (M->Mode != LastMode) { LastMode = M->Mode; RebuildIn = 3; Invalidate(EInvalidateWidgetReason::Layout); }
	if (RebuildIn > 0 && --RebuildIn == 0) BuiltOptions = -1;
	// rebuild the option / move buttons when the model changed; the old brushes die after the old widgets
	if (M->OptionsRev != BuiltOptions && ChoiceHost.IsValid())
	{
		BuiltOptions = M->OptionsRev; TArray<TSharedPtr<FSlateBrush>> Old = MoveTemp(KeepOpt); KeepOpt.Reset();
		Sink = &KeepOpt; ChoiceHost->SetContent(MakeOptions()); Sink = &Keep; Invalidate(EInvalidateWidgetReason::Layout);
		ChoiceHost->SlatePrepass(GetPrepassLayoutScaleMultiplier());   // measure the new buttons now, not a frame late
	}
	if (M->MovesRev != BuiltMoves && MovesHost.IsValid())
	{
		BuiltMoves = M->MovesRev; TArray<TSharedPtr<FSlateBrush>> Old = MoveTemp(KeepMov); KeepMov.Reset();
		Sink = &KeepMov; MovesHost->SetContent(MakeMoves()); Sink = &Keep; Invalidate(EInvalidateWidgetReason::Layout);
	}
}
