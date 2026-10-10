// Pokebox Next — all game UI in Slate (code only, no widget assets): comic panels, Bangers titles, Barlow text.
#pragma once
#include "CoreMinimal.h"
#include "Widgets/SCompoundWidget.h"
#include "Styling/SlateBrush.h"

class SVerticalBox; class SHorizontalBox; class SBox; class SCanvas; class SWrapBox; class UTexture2D;

enum class EPBXUIMode : uint8 { None, Explore, Dialogue, Choice, Battle, Menu };

struct FPBXOption
{
	FString Title, Sub; FLinearColor Color = FLinearColor::White; bool bEnabled = true;
	TSharedPtr<FSlateBrush> Image; // big card picture (starter choice)
	FString Key;                   // shortcut label ("1", "E"...)
};

struct FPBXPlate { FString Name, Type, Status; int32 Lv = 1, HP = 1, MaxHP = 1, Energy = 0; bool bShow = false; float ShownHP = -1.f; };

struct FPBXFloater { FVector World = FVector::ZeroVector; FString Text; FLinearColor Color = FLinearColor::White; float T = 99.f; FVector2D Screen = FVector2D::ZeroVector; float Scale = 1.f; };

struct FPBXUIModel
{
	EPBXUIMode Mode = EPBXUIMode::None;
	float Fade = 1.f;                          // 0 = clear, 1 = black
	// explore HUD
	FString Chapter, Objective; int32 Distance = -1; float ArrowAngle = 0.f; bool bArrow = false;
	FString Prompt;
	struct FToast { FString Text; float T = 0.f; };
	TArray<FToast> Toasts;
	FPBXPlate Partner;
	// dialogue
	FString Speaker, Line; float Visible = 0.f; FLinearColor SpeakerColor = FLinearColor(1, .82f, .2f);
	// choice / menus
	FString ChoiceTitle, ChoiceSub; TArray<FPBXOption> Options; int32 Selected = 0; bool bCards = false; int32 OptionsRev = 0;
	TFunction<void(int32)> OnPick;
	// battle
	FPBXPlate Plate[2]; FString Log, Banner; float BannerT = 0.f; bool bMoves = false; int32 MovesRev = 0;
	TArray<FPBXOption> Moves; int32 MoveSel = 0; TFunction<void(int32)> OnMove;
	FPBXFloater Floaters[8];
	FString BigTitle, BigSub; float BigT = 0.f; // centered splash (chapter start, "Gotcha!", level complete)
	float ShakeT = 0.f;
};

namespace PBXUI
{
	FSlateFontInfo Font(const TCHAR* Kind, int32 Size, int32 Outline = 0);   // Kind: "title" (Bangers) | "bold" | "body"
	TSharedPtr<FSlateBrush> TextureBrush(UTexture2D* T, FVector2D Size);
}

class SPBXHud : public SCompoundWidget
{
public:
	SLATE_BEGIN_ARGS(SPBXHud) {}
	SLATE_END_ARGS()
	void Construct(const FArguments& Args, TSharedPtr<FPBXUIModel> InModel);
	virtual void Tick(const FGeometry& G, const double Time, const float Dt) override;
private:
	TSharedPtr<FPBXUIModel> M;
	TSharedPtr<SBox> ChoiceHost, MovesHost;
	int32 BuiltOptions = -1, BuiltMoves = -1;
	TSharedRef<SWidget> MakeOptions();
	TSharedRef<SWidget> MakeMoves();
	TSharedRef<SWidget> MakePlate(int32 Side);
	TSharedRef<SWidget> Panel(TSharedRef<SWidget> Content, FLinearColor Fill = FLinearColor(1, .98f, .93f), float Pad = 16.f);
	TArray<TSharedPtr<FSlateBrush>> Keep, KeepOpt, KeepMov;
	TArray<TSharedPtr<FSlateBrush>>* Sink = nullptr;
};
