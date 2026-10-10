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

/** 2D UI particle (sparks / confetti), screen pixels in HUD space */
struct FPBXSpark { FVector2D P = FVector2D::ZeroVector, V = FVector2D::ZeroVector; FLinearColor C = FLinearColor::White; float Size = 8.f, Life = 1.f, Age = 0.f, Grav = 0.f, Phase = 0.f, Spin = 0.f; bool bConfetti = false; };

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
	// battle juice
	FLinearColor BannerColor = FLinearColor(.08f, .07f, .1f, .9f); float BannerMax = 1.f;   // BannerMax = BannerT when it was set (pop-in timing)
	float MovesIn = 0.f;                                                                     // 0..1 slide-in of the move panel
	float FlashT = 0.f; FLinearColor FlashColor = FLinearColor::White;     // full-screen flash on big hits
	float IntroT = 0.f; FString IntroA, IntroB; FLinearColor IntroColA = FLinearColor(.9f, .3f, .2f), IntroColB = FLinearColor(.2f, .45f, .9f);
	TArray<FPBXSpark> Sparks; FVector2D ViewSize = FVector2D(1920, 1080); float Time = 0.f;
};

namespace PBXUI
{
	FSlateFontInfo Font(const TCHAR* Kind, int32 Size, int32 Outline = 0);   // Kind: "title" (Bangers) | "bold" | "body"
	TSharedPtr<FSlateBrush> TextureBrush(UTexture2D* T, FVector2D Size);
	/** UI particles: a burst of glowing sparks at a screen point / confetti raining over the whole screen */
	void SparkBurst(FPBXUIModel& M, FVector2D At, FLinearColor C, int32 N, float Speed = 650.f, float Size = 10.f);
	void Confetti(FPBXUIModel& M, int32 N);
	void TickSparks(FPBXUIModel& M, float Dt);
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
