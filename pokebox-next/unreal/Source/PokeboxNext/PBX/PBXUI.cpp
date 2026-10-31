#include "PBX/PBXUI.h"
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

static const FLinearColor InkC(.03f, .025f, .04f);
static const FLinearColor PaperC(1.f, .98f, .93f);
static const FLinearColor GoldC(1.f, .82f, .2f);
// 2026-10-31 (phase 7): calm, elegant UI for the realistic world — dark smoked-glass panels, thin warm rims, ivory text
static const FLinearColor TextC(.95f, .93f, .88f);
static const FLinearColor GlassC(.045f, .05f, .065f, .78f);
static const FLinearColor RimC(1.f, .88f, .62f, .55f);

FSlateFontInfo PBXUI::Font(const TCHAR* Kind, int32 Size, int32 Outline)
{
	static TMap<FString, TSharedPtr<const FCompositeFont>> Cache;
	const FString K = Kind;
	const TCHAR* File = K == TEXT("title") ? TEXT("BarlowCondensed-ExtraBold.ttf") : K == TEXT("bold") ? TEXT("BarlowCondensed-ExtraBold.ttf") : TEXT("BarlowCondensed-SemiBold.ttf");   // 2026-10-31: no comic Bangers in the realistic look
	const FString Path = FPaths::ProjectContentDir() / TEXT("PBX/Fonts") / File;
	TSharedPtr<const FCompositeFont>& F = Cache.FindOrAdd(Path);
	if (!F.IsValid())
	{
		if (FPaths::FileExists(Path)) F = MakeShared<FStandaloneCompositeFont>(NAME_None, Path, EFontHinting::Default, EFontLoadingPolicy::LazyLoad);
		else { FSlateFontInfo D = FCoreStyle::GetDefaultFontStyle(K == TEXT("body") ? "Regular" : "Bold", Size); if (Outline) { D.OutlineSettings.OutlineSize = Outline; D.OutlineSettings.OutlineColor = InkC; } return D; }
	}
	FSlateFontInfo I(F, Size);
	if (K == TEXT("title")) I.LetterSpacing = 90;                  // wide-tracked capitals read calm and elegant
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

TSharedRef<SWidget> SPBXHud::Panel(TSharedRef<SWidget> Content, FLinearColor Fill, float Pad)
{
	const bool bLight = Fill.R + Fill.G + Fill.B > 1.5f;        // the old paper colours become smoked glass
	TSharedPtr<FSlateBrush> B = MakeShared<FSlateRoundedBoxBrush>(bLight ? GlassC : Fill, 12.f, RimC, 1.5f); Sink->Add(B);
	return SNew(SBorder).BorderImage(B.Get()).Padding(Pad)[Content];
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
	TSharedPtr<FSlateBrush> TagB = MakeShared<FSlateRoundedBoxBrush>(FLinearColor(.07f, .065f, .06f, .92f), 8.f, GoldC, 1.5f); Keep.Add(TagB);   // speaker name: dark tab, gold rim
	TSharedPtr<FSlateBrush> Dark = MakeShared<FSlateColorBrush>(FLinearColor(0, 0, 0, .55f)); Keep.Add(Dark);
	TSharedPtr<FSlateBrush> LogB = MakeShared<FSlateRoundedBoxBrush>(FLinearColor(.05f, .045f, .07f, .82f), 8.f, FLinearColor(1, .82f, .2f, .9f), 2.f); Keep.Add(LogB);
	TSharedPtr<FSlateBrush> BannerB = MakeShared<FSlateColorBrush>(FLinearColor::White); Keep.Add(BannerB);

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
			SNew(SBox).WidthOverride(560).Visibility_Lambda([this] { return Vis(M->Mode == EPBXUIMode::Explore && !M->Objective.IsEmpty()); })
			[
				Panel(SNew(SVerticalBox)
					+ SVerticalBox::Slot().AutoHeight()[SNew(STextBlock).Text_Lambda([this] { return FText::FromString(M->Chapter.ToUpper()); }).Font(PBXUI::Font(TEXT("bold"), 15)).ColorAndOpacity(FLinearColor(.78f, .72f, .62f))]
					+ SVerticalBox::Slot().AutoHeight().Padding(0, 2, 0, 0)
					[
						SNew(SHorizontalBox)
						+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0, 0, 10, 0)
						[
							SNew(STextBlock).Text(FText::FromString(TEXT(">"))).Font(PBXUI::Font(TEXT("title"), 34, 2)).ColorAndOpacity(GoldC)
							.Visibility_Lambda([this] { return M->bArrow ? EVisibility::HitTestInvisible : EVisibility::Hidden; })
							.RenderTransform_Lambda([this] { return FSlateRenderTransform(FQuat2D(FMath::DegreesToRadians(M->ArrowAngle))); }).RenderTransformPivot(FVector2D(.5f, .5f))
						]
						+ SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)[SNew(STextBlock).Text_Lambda([this] { return FText::FromString(M->Objective); }).Font(PBXUI::Font(TEXT("bold"), 25)).ColorAndOpacity(TextC).AutoWrapText(true)]
						+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(10, 0, 0, 0)[SNew(STextBlock).Text_Lambda([this] { return FText::FromString(M->Distance >= 0 ? FString::Printf(TEXT("%d m"), M->Distance) : FString()); }).Font(PBXUI::Font(TEXT("bold"), 22)).ColorAndOpacity(GoldC)]
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
						+ SHorizontalBox::Slot().FillWidth(1)[SNew(STextBlock).Text_Lambda([this] { return FText::FromString(M->Partner.Name); }).Font(PBXUI::Font(TEXT("bold"), 24)).ColorAndOpacity(TextC)]
						+ SHorizontalBox::Slot().AutoWidth()[SNew(STextBlock).Text_Lambda([this] { return FText::FromString(FString::Printf(TEXT("Lv %d"), M->Partner.Lv)); }).Font(PBXUI::Font(TEXT("bold"), 20)).ColorAndOpacity(FLinearColor(.8f, .76f, .7f))]
					]
					+ SVerticalBox::Slot().AutoHeight().Padding(0, 6, 0, 0)
					[
						SNew(SOverlay)
						+ SOverlay::Slot()[SNew(SBox).HeightOverride(12).WidthOverride(298)[SNew(SImage).Image(White()).ColorAndOpacity(FLinearColor(.15f, .13f, .14f))]]
						+ SOverlay::Slot().HAlign(HAlign_Left)[SNew(SBox).HeightOverride(12).WidthOverride_Lambda([this] { return FOptionalSize(298.f * FMath::Clamp(float(M->Partner.HP) / FMath::Max(1, M->Partner.MaxHP), 0.f, 1.f)); })
							[SNew(SImage).Image(White()).ColorAndOpacity_Lambda([this] { const float k = float(M->Partner.HP) / FMath::Max(1, M->Partner.MaxHP); return FSlateColor(k > .5f ? FLinearColor(.3f, .8f, .35f) : k > .2f ? FLinearColor(.95f, .75f, .2f) : FLinearColor(.9f, .25f, .2f)); })]]
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
			+ SOverlay::Slot().HAlign(HAlign_Right).VAlign(VAlign_Bottom).Padding(48, 0, 48, 400)[MakePlate(0)]
			// battle log: slim dark strip under the top bar
			+ SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Top).Padding(0, 66)
			[
				SNew(SBox).WidthOverride(820).Visibility_Lambda([this] { return Vis(!M->Log.IsEmpty() && M->IntroT <= 0.f && M->BannerT <= 0.f); })
				[
					SNew(SBorder).BorderImage(LogB.Get()).Padding(FMargin(26, 10))
					[SNew(STextBlock).Text_Lambda([this] { return FText::FromString(M->Log); }).Font(PBXUI::Font(TEXT("bold"), 27, 1)).ColorAndOpacity(FLinearColor::White).AutoWrapText(true).Justification(ETextJustify::Center)]
				]
			]
			+ SOverlay::Slot().HAlign(HAlign_Right).VAlign(VAlign_Bottom).Padding(48, 78)
			[
				SAssignNew(MovesHost, SBox).WidthOverride(700).Visibility_Lambda([this] { return M->bMoves ? EVisibility::Visible : EVisibility::Collapsed; })
				.RenderTransform_Lambda([this] { const float k = FMath::Clamp(M->MovesIn, 0.f, 1.f); return FSlateRenderTransform(FVector2D((1.f - FMath::Sin(k * PI * .5f)) * 760.f, 0)); })
			]
			// banner: slanted colour strip that pops in (wild appeared / super effective / critical)
			+ SOverlay::Slot().HAlign(HAlign_Fill).VAlign(VAlign_Center).Padding(FMargin(0, 120, 0, 0))   // between the foe and your Echo, clear of the plates
			[
				SNew(SBorder).BorderImage(BannerB.Get()).BorderBackgroundColor_Lambda([this] { return FSlateColor(M->BannerColor); }).Padding(FMargin(0, 18)).HAlign(HAlign_Center)
				.Visibility_Lambda([this] { return Vis(M->BannerT > 0.f && !M->Banner.IsEmpty()); })
				.RenderTransform_Lambda([this] { const float In = FMath::Clamp((M->BannerMax - M->BannerT) * 6.f, 0.f, 1.f); const float Out = FMath::Clamp(M->BannerT * 5.f, 0.f, 1.f);
					return XForm(-.18f, 1.f, FMath::Max(.001f, In * Out)); }).RenderTransformPivot(FVector2D(.5f, .5f))
				[SNew(STextBlock).Text_Lambda([this] { return FText::FromString(M->Banner.ToUpper()); }).Font(PBXUI::Font(TEXT("title"), 84, 5)).ColorAndOpacity(FLinearColor::White)
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
						SNew(SBorder).BorderImage(White()).BorderBackgroundColor_Lambda([this] { return FSlateColor(M->IntroColA); }).HAlign(HAlign_Center).VAlign(VAlign_Center)
						[SNew(STextBlock).Text_Lambda([this] { return FText::FromString(M->IntroA.ToUpper()); }).Font(PBXUI::Font(TEXT("title"), 88, 5)).ColorAndOpacity(FLinearColor::White)]
					]
				]
				+ SOverlay::Slot().VAlign(VAlign_Center).HAlign(HAlign_Right).Padding(0, 170, 0, 0)
				[
					SNew(SBox).WidthOverride_Lambda([this] { return FOptionalSize(M->ViewSize.X * .62f); }).HeightOverride(150)
					.RenderTransform_Lambda([this] { const float k = FMath::Clamp((1.75f - M->IntroT) * 4.f, 0.f, 1.f) * FMath::Clamp(M->IntroT * 4.f, 0.f, 1.f); return XForm(-.25f, 1.f, 1.f, FVector2D((1.f - k) * M->ViewSize.X * .7f, 0)); })
					[
						SNew(SBorder).BorderImage(White()).BorderBackgroundColor_Lambda([this] { return FSlateColor(M->IntroColB); }).HAlign(HAlign_Center).VAlign(VAlign_Center)
						[SNew(STextBlock).Text_Lambda([this] { return FText::FromString(M->IntroB.ToUpper()); }).Font(PBXUI::Font(TEXT("title"), 88, 5)).ColorAndOpacity(FLinearColor::White)]
					]
				]
				+ SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Center)
				[
					SNew(STextBlock).Text(FText::FromString(TEXT("VS"))).Font(PBXUI::Font(TEXT("title"), 190, 8)).ColorAndOpacity(GoldC)
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
							+ SVerticalBox::Slot().FillHeight(1).Padding(8, 14, 8, 0)[SNew(STextBlock).Text_Lambda([this] { return FText::FromString(M->Line.Left(FMath::FloorToInt(M->Visible))); }).Font(PBXUI::Font(TEXT("body"), 31)).ColorAndOpacity(TextC).AutoWrapText(true)]
							+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Right)[SNew(STextBlock).Text(FText::FromString(TEXT("E / click  >"))).Font(PBXUI::Font(TEXT("bold"), 18)).ColorAndOpacity(FLinearColor(.72f, .68f, .62f))
								.Visibility_Lambda([this] { return M->Visible >= M->Line.Len() ? EVisibility::HitTestInvisible : EVisibility::Hidden; })]
						], PaperC, 22.f)
				]
				+ SOverlay::Slot().HAlign(HAlign_Left).VAlign(VAlign_Top).Padding(30, 0, 0, 0)
				[
					SNew(SBorder).BorderImage(TagB.Get()).Padding(FMargin(18, 4)).Visibility_Lambda([this] { return Vis(!M->Speaker.IsEmpty()); })
					[SNew(STextBlock).Text_Lambda([this] { return FText::FromString(M->Speaker); }).Font(PBXUI::Font(TEXT("title"), 30)).ColorAndOpacity(GoldC)]
				]
			]
		]

		// ---------------- choice / menus (center)
		+ SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Center)
		[
			SNew(SVerticalBox).Visibility_Lambda([this] { return (M->Mode == EPBXUIMode::Choice || M->Mode == EPBXUIMode::Menu) ? EVisibility::Visible : EVisibility::Collapsed; })
			+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center)[SNew(STextBlock).Text_Lambda([this] { return FText::FromString(M->ChoiceTitle); }).Font(PBXUI::Font(TEXT("title"), 76, 4)).ColorAndOpacity(FLinearColor::White)]
			+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center).Padding(0, 0, 0, 22)[SNew(STextBlock).Text_Lambda([this] { return FText::FromString(M->ChoiceSub); }).Font(PBXUI::Font(TEXT("bold"), 26, 2)).ColorAndOpacity(TextC).Justification(ETextJustify::Center)]
			+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center)[SAssignNew(ChoiceHost, SBox)]
		]

		// ---------------- big splash (chapter, captured, complete)
		+ SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Center).Padding(0, 0, 0, 420)   // high enough to clear faces
		[
			SNew(SVerticalBox).Visibility_Lambda([this] { return Vis(M->BigT > 0.f && !M->BigTitle.IsEmpty()); })
			+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center)[SNew(STextBlock).Text_Lambda([this] { return FText::FromString(M->BigTitle); }).Font(PBXUI::Font(TEXT("title"), 96, 5))
				.ColorAndOpacity_Lambda([this] { FLinearColor C = GoldC; C.A = FMath::Clamp(M->BigT, 0.f, 1.f); return FSlateColor(C); })]
			+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center)[SNew(STextBlock).Text_Lambda([this] { return FText::FromString(M->BigSub); }).Font(PBXUI::Font(TEXT("bold"), 32, 3))
				.ColorAndOpacity_Lambda([this] { return FSlateColor(FLinearColor(1, 1, 1, FMath::Clamp(M->BigT, 0.f, 1.f))); })]
		]

		// ---------------- intro "ink myth" overlay (Sigil & Spark)
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
			SNew(SBorder).Visibility_Lambda([this] { return M->SubA > .01f && !M->Subtitle.IsEmpty() ? EVisibility::HitTestInvisible : EVisibility::Collapsed; })
			.BorderImage(White()).BorderBackgroundColor_Lambda([this] { return FSlateColor(FLinearColor(0, 0, 0, .55f * M->SubA)); }).Padding(FMargin(22, 8))
			[
				SNew(STextBlock).Text_Lambda([this] { return FText::FromString(M->SubSpeaker.IsEmpty() ? M->Subtitle : M->SubSpeaker + TEXT(":  ") + M->Subtitle); })
				.Font(PBXUI::Font(TEXT("body"), 26, 1)).Justification(ETextJustify::Center).WrapTextAt(1150.f)   // fixed width: AutoWrapText collapsed the bar to 3-5 short lines (r61)
				.ColorAndOpacity_Lambda([this] { return FSlateColor(FLinearColor(1, 1, 1, M->SubA)); })
			]
		]
		+ SOverlay::Slot().HAlign(HAlign_Right).VAlign(VAlign_Bottom).Padding(0, 0, 40, 30)
		[
			SNew(STextBlock).Visibility_Lambda([this] { return M->Letterbox > .9f ? EVisibility::HitTestInvisible : EVisibility::Collapsed; })
			.Text(FText::FromString(TEXT("E  skip"))).Font(PBXUI::Font(TEXT("bold"), 18)).ColorAndOpacity(FLinearColor(1, 1, 1, .55f))
		]

		// ---------------- fade
		+ SOverlay::Slot()
		[
			SNew(SImage).Image(White()).Visibility(EVisibility::HitTestInvisible).ColorAndOpacity_Lambda([this] { return FSlateColor(FLinearColor(0, 0, 0, M->Fade)); })
		]
	];
}

TSharedRef<SWidget> SPBXHud::MakePlate(int32 Side)
{
	auto P = [this, Side]() -> FPBXPlate& { return M->Plate[Side]; };
	TSharedPtr<FSlateBrush> Bg = MakeShared<FSlateRoundedBoxBrush>(FLinearColor(.045f, .04f, .06f, .9f), 14.f, FLinearColor(1, 1, 1, .9f), 3.f); Sink->Add(Bg);
	TSharedPtr<FSlateBrush> Badge = MakeShared<FSlateRoundedBoxBrush>(FLinearColor::White, 8.f); Sink->Add(Badge);
	TSharedPtr<FSlateBrush> Bar = MakeShared<FSlateRoundedBoxBrush>(FLinearColor::White, 6.f); Sink->Add(Bar);
	TSharedPtr<FSlateBrush> Pip = MakeShared<FSlateRoundedBoxBrush>(FLinearColor::White, 9.f, FLinearColor(1, 1, 1, .5f), 1.5f); Sink->Add(Pip);
	const float W = 420.f;
	TSharedRef<SHorizontalBox> Pips = SNew(SHorizontalBox);
	for (int32 i = 0; i < 5; i++)
		Pips->AddSlot().AutoWidth().Padding(3, 0)
		[
			SNew(SBox).WidthOverride(18).HeightOverride(18)
			[
				SNew(SImage).Image(Pip.Get()).ColorAndOpacity_Lambda([this, P, i]
				{
					const bool bOn = i < P().Energy; FLinearColor C = PBXData::TypeColor(P().Type);
					if (!bOn) return FSlateColor(FLinearColor(.18f, .17f, .2f));
					const float Glow = 1.f + .35f * FMath::Sin(M->Time * 6.f + i);   // charged pips shimmer
					return FSlateColor(FLinearColor(C.R * Glow, C.G * Glow, C.B * Glow, 1.f));
				})
			]
		];
	return SNew(SBox).WidthOverride(W).Visibility_Lambda([this, Side] { return Vis(M->Plate[Side].bShow); })
		// slides in from its screen edge after the VS intro
		.RenderTransform_Lambda([this, Side] { const float k = M->IntroT > 0.f ? 0.f : 1.f; (void)k; const float In = FMath::Clamp(1.f - M->IntroT * 2.f, 0.f, 1.f); return XForm(0.f, 1.f, 1.f, FVector2D((1.f - In) * (Side == 0 ? -520.f : 520.f), 0)); })
	[
		SNew(SBorder).BorderImage(Bg.Get()).Padding(FMargin(18, 12))
		[
			SNew(SVerticalBox)
			+ SVerticalBox::Slot().AutoHeight()
			[
				SNew(SHorizontalBox)
				+ SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)[SNew(STextBlock).Text_Lambda([P] { return FText::FromString(P().Name.ToUpper()); }).Font(PBXUI::Font(TEXT("title"), 38, 2)).ColorAndOpacity(FLinearColor::White)]
				+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(8, 0)
				[
					SNew(SBorder).BorderImage(Badge.Get()).BorderBackgroundColor_Lambda([P] { return FSlateColor(PBXData::TypeColor(P().Type)); }).Padding(FMargin(10, 2))
					[SNew(STextBlock).Text_Lambda([P] { return FText::FromString(PBXData::InkName(P().Type).ToUpper()); }).Font(PBXUI::Font(TEXT("bold"), 17, 1)).ColorAndOpacity(FLinearColor::White)]
				]
				+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[SNew(STextBlock).Text_Lambda([P] { return FText::FromString(FString::Printf(TEXT("Lv %d"), P().Lv)); }).Font(PBXUI::Font(TEXT("title"), 28, 2)).ColorAndOpacity(GoldC)]
			]
			+ SVerticalBox::Slot().AutoHeight().Padding(0, 6, 0, 0)
			[
				SNew(SOverlay)
				+ SOverlay::Slot()[SNew(SBox).HeightOverride(20).WidthOverride(W - 36)[SNew(SImage).Image(Bar.Get()).ColorAndOpacity(FLinearColor(.16f, .14f, .17f))]]
				// damage trail (white, catches up with the real HP)
				+ SOverlay::Slot().HAlign(HAlign_Left)[SNew(SBox).HeightOverride(20).WidthOverride_Lambda([P, W] { const float Shown = P().ShownHP < 0.f ? P().HP : P().ShownHP; return FOptionalSize((W - 36) * FMath::Clamp(Shown / FMath::Max(1, P().MaxHP), 0.f, 1.f)); })
					[SNew(SImage).Image(Bar.Get()).ColorAndOpacity(FLinearColor(1.f, .95f, .85f))]]
				+ SOverlay::Slot().HAlign(HAlign_Left)[SNew(SBox).HeightOverride(20).WidthOverride_Lambda([P, W] { return FOptionalSize((W - 36) * FMath::Clamp(float(FMath::Max(0, P().HP)) / FMath::Max(1, P().MaxHP), 0.f, 1.f)); })
					[SNew(SImage).Image(Bar.Get()).ColorAndOpacity_Lambda([this, P] { const float k = float(P().HP) / FMath::Max(1, P().MaxHP);
						FLinearColor C = k > .5f ? FLinearColor(.25f, .9f, .4f) : k > .2f ? FLinearColor(1.f, .78f, .15f) : FLinearColor(1.f, .22f, .18f);
						if (k <= .2f) C *= 1.f + .4f * FMath::Abs(FMath::Sin(M->Time * 8.f));   // low HP blinks
						return FSlateColor(C); })]]
				+ SOverlay::Slot().HAlign(HAlign_Right).VAlign(VAlign_Center).Padding(0, 0, 8, 0)[SNew(STextBlock).Text_Lambda([P] { return FText::FromString(FString::Printf(TEXT("%d / %d"), FMath::Max(0, P().HP), P().MaxHP)); }).Font(PBXUI::Font(TEXT("bold"), 16, 1)).ColorAndOpacity(FLinearColor::White)]
			]
			+ SVerticalBox::Slot().AutoHeight().Padding(0, 8, 0, 0)
			[
				SNew(SHorizontalBox)
				+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0, 0, 6, 0)[SNew(STextBlock).Text(FText::FromString(TEXT("ENERGY"))).Font(PBXUI::Font(TEXT("bold"), 15)).ColorAndOpacity(FLinearColor(.7f, .68f, .75f))]
				+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[Pips]
				+ SHorizontalBox::Slot().FillWidth(1).HAlign(HAlign_Right).VAlign(VAlign_Center)
				[
					SNew(SBorder).BorderImage(Badge.Get()).BorderBackgroundColor(FLinearColor(.95f, .45f, .15f)).Padding(FMargin(8, 1)).Visibility_Lambda([P] { return Vis(!P().Status.IsEmpty()); })
					[SNew(STextBlock).Text_Lambda([P] { return FText::FromString(P().Status.ToUpper()); }).Font(PBXUI::Font(TEXT("bold"), 15, 1)).ColorAndOpacity(FLinearColor::White)]
				]
			]
		]
	];
}

TSharedRef<SWidget> SPBXHud::MakeOptions()
{
	TSharedRef<SHorizontalBox> Row = SNew(SHorizontalBox);
	TSharedRef<SVerticalBox> Col = SNew(SVerticalBox);
	for (int32 i = 0; i < M->Options.Num(); i++)
	{
		const FPBXOption& O = M->Options[i];
		TSharedPtr<FSlateBrush> Sel = MakeShared<FSlateRoundedBoxBrush>(FLinearColor(.13f, .12f, .1f, .9f), 12.f, GoldC, 2.5f); Sink->Add(Sel);
		TSharedPtr<FSlateBrush> Nor = MakeShared<FSlateRoundedBoxBrush>(GlassC, 12.f, RimC, 1.2f); Sink->Add(Nor);
		TSharedPtr<FSlateBrush> Off = MakeShared<FSlateRoundedBoxBrush>(FLinearColor(.03f, .03f, .04f, .6f), 12.f, FLinearColor(1, 1, 1, .15f), 1.f); Sink->Add(Off);
		auto OnDown = [this, i](const FGeometry&, const FPointerEvent&) { M->Selected = i; if (M->OnPick && M->Options.IsValidIndex(i) && M->Options[i].bEnabled) M->OnPick(i); return FReply::Handled(); };
		auto Brush = [this, i, Sel, Nor, Off] { return !M->Options.IsValidIndex(i) || !M->Options[i].bEnabled ? Off.Get() : M->Selected == i ? Sel.Get() : Nor.Get(); };
		TSharedRef<SVerticalBox> Inner = SNew(SVerticalBox);
		if (M->bCards && O.Image.IsValid())
			Inner->AddSlot().AutoHeight().HAlign(HAlign_Center).Padding(0, 0, 0, 10)[SNew(SBox).WidthOverride(250).HeightOverride(349)[SNew(SImage).Image(O.Image.Get())]];
		Inner->AddSlot().AutoHeight().HAlign(M->bCards ? HAlign_Center : HAlign_Left)[SNew(STextBlock).Text(FText::FromString(O.Title)).Font(PBXUI::Font(M->bCards ? TEXT("title") : TEXT("bold"), M->bCards ? 40 : 32)).ColorAndOpacity(TextC)];
		if (!O.Sub.IsEmpty())
			Inner->AddSlot().AutoHeight().HAlign(M->bCards ? HAlign_Center : HAlign_Left)[SNew(STextBlock).Text(FText::FromString(O.Sub)).Font(PBXUI::Font(TEXT("bold"), 20)).ColorAndOpacity(O.Color * .8f).WrapTextAt(M->bCards ? 0.f : 510.f)];   // fixed width: auto-wrap needs a second layout pass and showed stacked lines on first open
		TSharedRef<SWidget> Btn = SNew(SBorder).BorderImage_Lambda(Brush).Padding(M->bCards ? FMargin(14) : FMargin(22, 10)).OnMouseButtonDown_Lambda(OnDown)
			.RenderTransform_Lambda([this, i] { return FSlateRenderTransform(M->Selected == i ? 1.04f : 1.f); }).RenderTransformPivot(FVector2D(.5f, .5f))[Inner];
		if (M->bCards) Row->AddSlot().AutoWidth().Padding(14, 0)[SNew(SBox).WidthOverride(300).HeightOverride(470)[Btn]];
		else Col->AddSlot().AutoHeight().Padding(0, 6)[SNew(SBox).WidthOverride(560)[Btn]];
	}
	if (M->bCards) return SNew(SBox).WidthOverride(328.f * FMath::Max(1, M->Options.Num())).HeightOverride(470.f)[Row];   // explicit size: the card row came out zero-sized (all three cards drawn on one spot)
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
		TSharedPtr<FSlateBrush> Card = MakeShared<FSlateRoundedBoxBrush>(FLinearColor(Base.R * .55f, Base.G * .55f, Base.B * .55f, .97f), 10.f, FLinearColor(1, 1, 1, .85f), 3.f); Sink->Add(Card);
		TSharedPtr<FSlateBrush> Sel = MakeShared<FSlateRoundedBoxBrush>(FLinearColor(Base.R * .8f, Base.G * .8f, Base.B * .8f, 1.f), 10.f, GoldC, 6.f); Sink->Add(Sel);
		TSharedPtr<FSlateBrush> Off = MakeShared<FSlateRoundedBoxBrush>(FLinearColor(.2f, .19f, .22f, .9f), 10.f, FLinearColor(.4f, .4f, .42f), 2.f); Sink->Add(Off);
		TSharedPtr<FSlateBrush> Key = MakeShared<FSlateRoundedBoxBrush>(FLinearColor(0, 0, 0, .45f), 16.f); Sink->Add(Key);
		auto Brush = [this, i, Sel, Card, Off] { return !M->Moves.IsValidIndex(i) || !M->Moves[i].bEnabled ? Off.Get() : M->MoveSel == i ? Sel.Get() : Card.Get(); };
		auto OnDown = [this, i](const FGeometry&, const FPointerEvent&) { M->MoveSel = i; if (M->OnMove && M->Moves.IsValidIndex(i) && M->Moves[i].bEnabled) M->OnMove(i); return FReply::Handled(); };
		auto OnHover = [this, i](const FGeometry&, const FPointerEvent&) { M->MoveSel = i; };
		Row->AddSlot().FillWidth(1).Padding(6, 0)
		[
			SNew(SBox).HeightOverride(84)
			.RenderTransform_Lambda([this, i] { const bool bSel = M->MoveSel == i; const float s = bSel ? 1.05f + .02f * FMath::Sin(M->Time * 7.f) : 1.f; return XForm(-.14f, s, s); })
			.RenderTransformPivot(FVector2D(.5f, .5f))
			[
				SNew(SBorder).BorderImage_Lambda(Brush).Padding(FMargin(14, 8)).OnMouseButtonDown_Lambda(OnDown).OnMouseMove_Lambda([OnHover](const FGeometry& G, const FPointerEvent& E) { OnHover(G, E); return FReply::Unhandled(); })
				[
					SNew(SHorizontalBox)
					+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0, 0, 12, 0)
					[SNew(SBorder).BorderImage(Key.Get()).Padding(FMargin(11, 2))[SNew(STextBlock).Text(FText::FromString(O.Key)).Font(PBXUI::Font(TEXT("title"), 30, 1)).ColorAndOpacity(GoldC)]]
					+ SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)
					[
						SNew(SVerticalBox)
						+ SVerticalBox::Slot().AutoHeight()[SNew(STextBlock).Text(FText::FromString(O.Title.ToUpper())).Font(PBXUI::Font(TEXT("title"), 31, 2)).ColorAndOpacity(FLinearColor::White)]
						+ SVerticalBox::Slot().AutoHeight()[SNew(STextBlock).Text(FText::FromString(O.Sub)).Font(PBXUI::Font(TEXT("bold"), 17)).ColorAndOpacity(FLinearColor(1, 1, 1, .8f))]
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
	M->ViewSize = FVector2D(G.GetLocalSize()); M->Time += Dt;
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
