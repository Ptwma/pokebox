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

static const FLinearColor InkC(.03f, .025f, .04f);
static const FLinearColor PaperC(1.f, .98f, .93f);
static const FLinearColor GoldC(1.f, .82f, .2f);

FSlateFontInfo PBXUI::Font(const TCHAR* Kind, int32 Size, int32 Outline)
{
	static TMap<FString, TSharedPtr<const FCompositeFont>> Cache;
	const FString K = Kind;
	const TCHAR* File = K == TEXT("title") ? TEXT("Bangers.ttf") : K == TEXT("bold") ? TEXT("BarlowCondensed-ExtraBold.ttf") : TEXT("BarlowCondensed-SemiBold.ttf");
	const FString Path = FPaths::ProjectContentDir() / TEXT("PBX/Fonts") / File;
	TSharedPtr<const FCompositeFont>& F = Cache.FindOrAdd(Path);
	if (!F.IsValid())
	{
		if (FPaths::FileExists(Path)) F = MakeShared<FStandaloneCompositeFont>(NAME_None, Path, EFontHinting::Default, EFontLoadingPolicy::LazyLoad);
		else { FSlateFontInfo D = FCoreStyle::GetDefaultFontStyle(K == TEXT("body") ? "Regular" : "Bold", Size); if (Outline) { D.OutlineSettings.OutlineSize = Outline; D.OutlineSettings.OutlineColor = InkC; } return D; }
	}
	FSlateFontInfo I(F, Size);
	if (Outline) { I.OutlineSettings.OutlineSize = Outline; I.OutlineSettings.OutlineColor = InkC; }
	return I;
}

TSharedPtr<FSlateBrush> PBXUI::TextureBrush(UTexture2D* T, FVector2D Size)
{
	TSharedPtr<FSlateBrush> B = MakeShared<FSlateBrush>();
	B->SetResourceObject(T); B->ImageSize = Size; B->DrawAs = ESlateBrushDrawType::Image;
	return B;
}

static const FSlateBrush* White() { return FCoreStyle::Get().GetBrush("WhiteBrush"); }

TSharedRef<SWidget> SPBXHud::Panel(TSharedRef<SWidget> Content, FLinearColor Fill, float Pad)
{
	TSharedPtr<FSlateBrush> B = MakeShared<FSlateRoundedBoxBrush>(Fill, 10.f, InkC, 4.f); Sink->Add(B);
	return SNew(SBorder).BorderImage(B.Get()).Padding(Pad)[Content];
}

static EVisibility Vis(bool b) { return b ? EVisibility::SelfHitTestInvisible : EVisibility::Collapsed; }

void SPBXHud::Construct(const FArguments& Args, TSharedPtr<FPBXUIModel> InModel)
{
	M = InModel; Sink = &Keep;
	ForceVolatile(true);
	TSharedPtr<FSlateBrush> TagB = MakeShared<FSlateRoundedBoxBrush>(GoldC, 6.f, InkC, 3.f); Keep.Add(TagB);
	TSharedPtr<FSlateBrush> Dark = MakeShared<FSlateColorBrush>(FLinearColor(0, 0, 0, .55f)); Keep.Add(Dark);

	TSharedRef<SCanvas> Canvas = SNew(SCanvas);
	for (int32 i = 0; i < 8; i++)
	{
		Canvas->AddSlot().Position_Lambda([this, i] { return M->Floaters[i].Screen; }).Size(FVector2D(360, 90)).HAlign(HAlign_Center).VAlign(VAlign_Center)
		[
			SNew(STextBlock).Text_Lambda([this, i] { return FText::FromString(M->Floaters[i].T < 1.2f ? M->Floaters[i].Text : FString()); })
			.Font(PBXUI::Font(TEXT("title"), 44, 3)).ColorAndOpacity_Lambda([this, i] { FLinearColor C = M->Floaters[i].Color; C.A = FMath::Clamp(1.2f - M->Floaters[i].T, 0.f, 1.f) * 2.f; return FSlateColor(C); })
			.RenderTransform_Lambda([this, i] { return FSlateRenderTransform(M->Floaters[i].Scale); }).RenderTransformPivot(FVector2D(.5f, .5f))
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
					+ SVerticalBox::Slot().AutoHeight()[SNew(STextBlock).Text_Lambda([this] { return FText::FromString(M->Chapter.ToUpper()); }).Font(PBXUI::Font(TEXT("bold"), 15)).ColorAndOpacity(FLinearColor(.35f, .3f, .28f))]
					+ SVerticalBox::Slot().AutoHeight().Padding(0, 2, 0, 0)
					[
						SNew(SHorizontalBox)
						+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0, 0, 10, 0)
						[
							SNew(STextBlock).Text(FText::FromString(TEXT(">"))).Font(PBXUI::Font(TEXT("title"), 34, 2)).ColorAndOpacity(GoldC)
							.Visibility_Lambda([this] { return M->bArrow ? EVisibility::HitTestInvisible : EVisibility::Hidden; })
							.RenderTransform_Lambda([this] { return FSlateRenderTransform(FQuat2D(FMath::DegreesToRadians(M->ArrowAngle))); }).RenderTransformPivot(FVector2D(.5f, .5f))
						]
						+ SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)[SNew(STextBlock).Text_Lambda([this] { return FText::FromString(M->Objective); }).Font(PBXUI::Font(TEXT("bold"), 25)).ColorAndOpacity(InkC).AutoWrapText(true)]
						+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(10, 0, 0, 0)[SNew(STextBlock).Text_Lambda([this] { return FText::FromString(M->Distance >= 0 ? FString::Printf(TEXT("%d m"), M->Distance) : FString()); }).Font(PBXUI::Font(TEXT("bold"), 22)).ColorAndOpacity(FLinearColor(.5f, .35f, .1f))]
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
						+ SHorizontalBox::Slot().FillWidth(1)[SNew(STextBlock).Text_Lambda([this] { return FText::FromString(M->Partner.Name); }).Font(PBXUI::Font(TEXT("bold"), 24)).ColorAndOpacity(InkC)]
						+ SHorizontalBox::Slot().AutoWidth()[SNew(STextBlock).Text_Lambda([this] { return FText::FromString(FString::Printf(TEXT("Lv %d"), M->Partner.Lv)); }).Font(PBXUI::Font(TEXT("bold"), 20)).ColorAndOpacity(FLinearColor(.4f, .35f, .3f))]
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
				Panel(SNew(STextBlock).Text_Lambda([this] { return FText::FromString(M->Prompt); }).Font(PBXUI::Font(TEXT("bold"), 26)).ColorAndOpacity(InkC), PaperC, 12.f)
			]
		]

		// ---------------- toasts (top-right)
		+ SOverlay::Slot().HAlign(HAlign_Right).VAlign(VAlign_Top).Padding(28, 24)
		[
			SNew(SVerticalBox)
			+ SVerticalBox::Slot().AutoHeight()[SNew(SBox).WidthOverride(430).Visibility_Lambda([this] { return Vis(M->Toasts.Num() > 0); })
				[Panel(SNew(STextBlock).Text_Lambda([this] { return FText::FromString(M->Toasts.Num() ? M->Toasts[0].Text : FString()); }).Font(PBXUI::Font(TEXT("bold"), 22)).ColorAndOpacity(InkC).AutoWrapText(true), FLinearColor(1, .95f, .75f), 12.f)]]
			+ SVerticalBox::Slot().AutoHeight().Padding(0, 8, 0, 0)[SNew(SBox).WidthOverride(430).Visibility_Lambda([this] { return Vis(M->Toasts.Num() > 1); })
				[Panel(SNew(STextBlock).Text_Lambda([this] { return FText::FromString(M->Toasts.Num() > 1 ? M->Toasts[1].Text : FString()); }).Font(PBXUI::Font(TEXT("bold"), 22)).ColorAndOpacity(InkC).AutoWrapText(true), FLinearColor(1, .95f, .75f), 12.f)]]
		]

		// ---------------- battle layer
		+ SOverlay::Slot()
		[
			SNew(SOverlay).Visibility_Lambda([this] { return M->Mode == EPBXUIMode::Battle ? EVisibility::SelfHitTestInvisible : EVisibility::Collapsed; })
			.RenderTransform_Lambda([this] { const float s = M->ShakeT > 0.f ? 10.f * M->ShakeT : 0.f; return FSlateRenderTransform(FVector2D(FMath::Sin(M->ShakeT * 90.f) * s, FMath::Cos(M->ShakeT * 70.f) * s)); })
			+ SOverlay::Slot().HAlign(HAlign_Right).VAlign(VAlign_Top).Padding(40, 36)[MakePlate(1)]
			+ SOverlay::Slot().HAlign(HAlign_Left).VAlign(VAlign_Bottom).Padding(40, 36)[MakePlate(0)]
			+ SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Top).Padding(0, 40)
			[
				SNew(SBox).WidthOverride(760).Visibility_Lambda([this] { return Vis(!M->Log.IsEmpty()); })
				[Panel(SNew(STextBlock).Text_Lambda([this] { return FText::FromString(M->Log); }).Font(PBXUI::Font(TEXT("bold"), 26)).ColorAndOpacity(InkC).AutoWrapText(true).Justification(ETextJustify::Center), PaperC, 12.f)]
			]
			+ SOverlay::Slot().HAlign(HAlign_Right).VAlign(VAlign_Bottom).Padding(40, 36)
			[
				SAssignNew(MovesHost, SBox).WidthOverride(620).Visibility_Lambda([this] { return M->bMoves ? EVisibility::Visible : EVisibility::Collapsed; })
			]
			+ SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Center)
			[
				SNew(SBorder).BorderImage(Dark.Get()).Padding(FMargin(80, 26)).Visibility_Lambda([this] { return Vis(M->BannerT > 0.f && !M->Banner.IsEmpty()); })
				[SNew(STextBlock).Text_Lambda([this] { return FText::FromString(M->Banner); }).Font(PBXUI::Font(TEXT("title"), 72, 4)).ColorAndOpacity(FLinearColor::White)]
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
							+ SVerticalBox::Slot().FillHeight(1).Padding(8, 14, 8, 0)[SNew(STextBlock).Text_Lambda([this] { return FText::FromString(M->Line.Left(FMath::FloorToInt(M->Visible))); }).Font(PBXUI::Font(TEXT("body"), 31)).ColorAndOpacity(InkC).AutoWrapText(true)]
							+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Right)[SNew(STextBlock).Text(FText::FromString(TEXT("E / click  >"))).Font(PBXUI::Font(TEXT("bold"), 18)).ColorAndOpacity(FLinearColor(.5f, .45f, .4f))
								.Visibility_Lambda([this] { return M->Visible >= M->Line.Len() ? EVisibility::HitTestInvisible : EVisibility::Hidden; })]
						], PaperC, 22.f)
				]
				+ SOverlay::Slot().HAlign(HAlign_Left).VAlign(VAlign_Top).Padding(30, 0, 0, 0)
				[
					SNew(SBorder).BorderImage(TagB.Get()).Padding(FMargin(18, 4)).Visibility_Lambda([this] { return Vis(!M->Speaker.IsEmpty()); })
					[SNew(STextBlock).Text_Lambda([this] { return FText::FromString(M->Speaker); }).Font(PBXUI::Font(TEXT("title"), 34)).ColorAndOpacity(InkC)]
				]
			]
		]

		// ---------------- choice / menus (center)
		+ SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Center)
		[
			SNew(SVerticalBox).Visibility_Lambda([this] { return (M->Mode == EPBXUIMode::Choice || M->Mode == EPBXUIMode::Menu) ? EVisibility::Visible : EVisibility::Collapsed; })
			+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center)[SNew(STextBlock).Text_Lambda([this] { return FText::FromString(M->ChoiceTitle); }).Font(PBXUI::Font(TEXT("title"), 76, 4)).ColorAndOpacity(FLinearColor::White)]
			+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center).Padding(0, 0, 0, 22)[SNew(STextBlock).Text_Lambda([this] { return FText::FromString(M->ChoiceSub); }).Font(PBXUI::Font(TEXT("bold"), 26, 2)).ColorAndOpacity(PaperC).Justification(ETextJustify::Center)]
			+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center)[SAssignNew(ChoiceHost, SBox)]
		]

		// ---------------- big splash (chapter, captured, complete)
		+ SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Center).Padding(0, 0, 0, 160)
		[
			SNew(SVerticalBox).Visibility_Lambda([this] { return Vis(M->BigT > 0.f && !M->BigTitle.IsEmpty()); })
			+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center)[SNew(STextBlock).Text_Lambda([this] { return FText::FromString(M->BigTitle); }).Font(PBXUI::Font(TEXT("title"), 96, 5))
				.ColorAndOpacity_Lambda([this] { FLinearColor C = GoldC; C.A = FMath::Clamp(M->BigT, 0.f, 1.f); return FSlateColor(C); })]
			+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center)[SNew(STextBlock).Text_Lambda([this] { return FText::FromString(M->BigSub); }).Font(PBXUI::Font(TEXT("bold"), 32, 3))
				.ColorAndOpacity_Lambda([this] { return FSlateColor(FLinearColor(1, 1, 1, FMath::Clamp(M->BigT, 0.f, 1.f))); })]
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
	return SNew(SBox).WidthOverride(420).Visibility_Lambda([this, Side] { return Vis(M->Plate[Side].bShow); })
	[
		Panel(SNew(SVerticalBox)
			+ SVerticalBox::Slot().AutoHeight()
			[
				SNew(SHorizontalBox)
				+ SHorizontalBox::Slot().FillWidth(1)[SNew(STextBlock).Text_Lambda([P] { return FText::FromString(P().Name); }).Font(PBXUI::Font(TEXT("title"), 36)).ColorAndOpacity(InkC)]
				+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[SNew(STextBlock).Text_Lambda([P] { return FText::FromString(FString::Printf(TEXT("%s  Lv %d"), *P().Type, P().Lv)); }).Font(PBXUI::Font(TEXT("bold"), 20)).ColorAndOpacity_Lambda([P] { return FSlateColor(PBXData::TypeColor(P().Type) * .75f); })]
			]
			+ SVerticalBox::Slot().AutoHeight().Padding(0, 4, 0, 0)
			[
				SNew(SOverlay)
				+ SOverlay::Slot()[SNew(SBox).HeightOverride(16).WidthOverride(388)[SNew(SImage).Image(White()).ColorAndOpacity(FLinearColor(.15f, .13f, .14f))]]
				+ SOverlay::Slot().HAlign(HAlign_Left)[SNew(SBox).HeightOverride(16).WidthOverride_Lambda([P] { const float Shown = P().ShownHP < 0.f ? P().HP : P().ShownHP; return FOptionalSize(388.f * FMath::Clamp(Shown / FMath::Max(1, P().MaxHP), 0.f, 1.f)); })
					[SNew(SImage).Image(White()).ColorAndOpacity_Lambda([P] { const float k = float(P().HP) / FMath::Max(1, P().MaxHP); return FSlateColor(k > .5f ? FLinearColor(.3f, .8f, .35f) : k > .2f ? FLinearColor(.95f, .75f, .2f) : FLinearColor(.9f, .25f, .2f)); })]]
			]
			+ SVerticalBox::Slot().AutoHeight().Padding(0, 4, 0, 0)
			[
				SNew(SHorizontalBox)
				+ SHorizontalBox::Slot().FillWidth(1)[SNew(STextBlock).Text_Lambda([P] { return FText::FromString(FString::Printf(TEXT("HP %d / %d   %s"), FMath::Max(0, P().HP), P().MaxHP, *P().Status.ToUpper())); }).Font(PBXUI::Font(TEXT("bold"), 18)).ColorAndOpacity(FLinearColor(.3f, .27f, .25f))]
				+ SHorizontalBox::Slot().AutoWidth()[SNew(STextBlock).Text_Lambda([P] { FString E; for (int32 i = 0; i < 5; i++) E += i < P().Energy ? TEXT("o") : TEXT("."); return FText::FromString(TEXT("Energy ") + E); }).Font(PBXUI::Font(TEXT("bold"), 18)).ColorAndOpacity(FLinearColor(.2f, .45f, .8f))]
			], PaperC, 14.f)
	];
}

TSharedRef<SWidget> SPBXHud::MakeOptions()
{
	TSharedRef<SHorizontalBox> Row = SNew(SHorizontalBox);
	TSharedRef<SVerticalBox> Col = SNew(SVerticalBox);
	for (int32 i = 0; i < M->Options.Num(); i++)
	{
		const FPBXOption& O = M->Options[i];
		TSharedPtr<FSlateBrush> Sel = MakeShared<FSlateRoundedBoxBrush>(PaperC, 12.f, GoldC, 7.f); Sink->Add(Sel);
		TSharedPtr<FSlateBrush> Nor = MakeShared<FSlateRoundedBoxBrush>(PaperC, 12.f, InkC, 4.f); Sink->Add(Nor);
		TSharedPtr<FSlateBrush> Off = MakeShared<FSlateRoundedBoxBrush>(FLinearColor(.7f, .68f, .64f), 12.f, InkC, 4.f); Sink->Add(Off);
		auto OnDown = [this, i](const FGeometry&, const FPointerEvent&) { M->Selected = i; if (M->OnPick && M->Options.IsValidIndex(i) && M->Options[i].bEnabled) M->OnPick(i); return FReply::Handled(); };
		auto Brush = [this, i, Sel, Nor, Off] { return !M->Options.IsValidIndex(i) || !M->Options[i].bEnabled ? Off.Get() : M->Selected == i ? Sel.Get() : Nor.Get(); };
		TSharedRef<SVerticalBox> Inner = SNew(SVerticalBox);
		if (M->bCards && O.Image.IsValid())
			Inner->AddSlot().AutoHeight().HAlign(HAlign_Center).Padding(0, 0, 0, 10)[SNew(SBox).WidthOverride(250).HeightOverride(349)[SNew(SImage).Image(O.Image.Get())]];
		Inner->AddSlot().AutoHeight().HAlign(M->bCards ? HAlign_Center : HAlign_Left)[SNew(STextBlock).Text(FText::FromString(O.Title)).Font(PBXUI::Font(M->bCards ? TEXT("title") : TEXT("bold"), M->bCards ? 40 : 32)).ColorAndOpacity(InkC)];
		if (!O.Sub.IsEmpty())
			Inner->AddSlot().AutoHeight().HAlign(M->bCards ? HAlign_Center : HAlign_Left)[SNew(STextBlock).Text(FText::FromString(O.Sub)).Font(PBXUI::Font(TEXT("bold"), 20)).ColorAndOpacity(O.Color * .8f).AutoWrapText(!M->bCards)];
		TSharedRef<SWidget> Btn = SNew(SBorder).BorderImage_Lambda(Brush).Padding(M->bCards ? FMargin(14) : FMargin(22, 10)).OnMouseButtonDown_Lambda(OnDown)
			.RenderTransform_Lambda([this, i] { return FSlateRenderTransform(M->Selected == i ? 1.04f : 1.f); }).RenderTransformPivot(FVector2D(.5f, .5f))[Inner];
		if (M->bCards) Row->AddSlot().AutoWidth().Padding(14, 0)[SNew(SBox).WidthOverride(300).HeightOverride(470)[Btn]];
		else Col->AddSlot().AutoHeight().Padding(0, 6)[SNew(SBox).WidthOverride(560)[Btn]];
	}
	if (M->bCards) return Row;
	return Col;
}

TSharedRef<SWidget> SPBXHud::MakeMoves()
{
	TSharedRef<SVerticalBox> Col = SNew(SVerticalBox);
	TSharedPtr<SHorizontalBox> Row;
	for (int32 i = 0; i < M->Moves.Num(); i++)
	{
		if (i % 2 == 0) { Row = SNew(SHorizontalBox); Col->AddSlot().AutoHeight().Padding(0, 5)[Row.ToSharedRef()]; }
		const FPBXOption& O = M->Moves[i];
		TSharedPtr<FSlateBrush> Sel = MakeShared<FSlateRoundedBoxBrush>(PaperC, 10.f, GoldC, 6.f); Sink->Add(Sel);
		TSharedPtr<FSlateBrush> Nor = MakeShared<FSlateRoundedBoxBrush>(PaperC, 10.f, InkC, 4.f); Sink->Add(Nor);
		TSharedPtr<FSlateBrush> Off = MakeShared<FSlateRoundedBoxBrush>(FLinearColor(.62f, .6f, .57f), 10.f, InkC, 4.f); Sink->Add(Off);
		auto Brush = [this, i, Sel, Nor, Off] { return !M->Moves.IsValidIndex(i) || !M->Moves[i].bEnabled ? Off.Get() : M->MoveSel == i ? Sel.Get() : Nor.Get(); };
		auto OnDown = [this, i](const FGeometry&, const FPointerEvent&) { M->MoveSel = i; if (M->OnMove && M->Moves.IsValidIndex(i) && M->Moves[i].bEnabled) M->OnMove(i); return FReply::Handled(); };
		Row->AddSlot().FillWidth(1).Padding(5, 0)
		[
			SNew(SBox).HeightOverride(76)[SNew(SBorder).BorderImage_Lambda(Brush).Padding(FMargin(16, 8)).OnMouseButtonDown_Lambda(OnDown)
			[
				SNew(SHorizontalBox)
				+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0, 0, 12, 0)[SNew(STextBlock).Text(FText::FromString(O.Key)).Font(PBXUI::Font(TEXT("title"), 30)).ColorAndOpacity(O.Color * .7f)]
				+ SHorizontalBox::Slot().FillWidth(1)
				[
					SNew(SVerticalBox)
					+ SVerticalBox::Slot().AutoHeight()[SNew(STextBlock).Text(FText::FromString(O.Title)).Font(PBXUI::Font(TEXT("bold"), 25)).ColorAndOpacity(InkC)]
					+ SVerticalBox::Slot().AutoHeight()[SNew(STextBlock).Text(FText::FromString(O.Sub)).Font(PBXUI::Font(TEXT("body"), 17)).ColorAndOpacity(FLinearColor(.35f, .32f, .3f))]
				]
			]]
		];
	}
	return Panel(Col, FLinearColor(.12f, .11f, .14f, .92f), 10.f);
}

void SPBXHud::Tick(const FGeometry& G, const double Time, const float Dt)
{
	SCompoundWidget::Tick(G, Time, Dt);
	// rebuild the option / move buttons when the model changed; the old brushes die after the old widgets
	if (M->OptionsRev != BuiltOptions && ChoiceHost.IsValid())
	{
		BuiltOptions = M->OptionsRev; TArray<TSharedPtr<FSlateBrush>> Old = MoveTemp(KeepOpt); KeepOpt.Reset();
		Sink = &KeepOpt; ChoiceHost->SetContent(MakeOptions()); Sink = &Keep; Invalidate(EInvalidateWidgetReason::Layout);
	}
	if (M->MovesRev != BuiltMoves && MovesHost.IsValid())
	{
		BuiltMoves = M->MovesRev; TArray<TSharedPtr<FSlateBrush>> Old = MoveTemp(KeepMov); KeepMov.Reset();
		Sink = &KeepMov; MovesHost->SetContent(MakeMoves()); Sink = &Keep; Invalidate(EInvalidateWidgetReason::Layout);
	}
}
