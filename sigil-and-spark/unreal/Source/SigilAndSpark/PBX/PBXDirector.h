// Sigil & Spark — runs the level: story (chapter 1), people, doors, wild Echoes, battles, menus, saving.
// Map data (spots, doors, NPCs, grass...) comes from Content/PBX/Data/<Map>.json, written by tools/blender_town.py.
// Start the game with -pbxauto to have it play itself through the whole chapter and take screenshots (test mode).
#pragma once
#include <atomic>
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/PlayerController.h"
#include "PBX/PBXCore.h"
#include "PBX/PBXUI.h"
#include "PBX/PBXGame.h"
#include "PBX/PBXFX.h"
class UAudioComponent; class USoundBase;
#include "PBXDirector.generated.h"

class APBXPlayer; class APBXNPC; class APBXEcho; class ACameraActor; class AStaticMeshActor; class UInputAction; class UInputMappingContext;
class UPBXGameSubsystem; class SPBXHud; class UTexture2D;
struct FInputActionValue;
class FJsonObject;

struct FPBXSpot { FVector Pos = FVector::ZeroVector; float Yaw = 0.f; };
struct FPBXDoor { FString Id, Label, LockedText; bool bLocked = false; FPBXSpot Outside, Inside; FVector OutDoor = FVector::ZeroVector, InDoor = FVector::ZeroVector; };
/** walking into an exit loads another level (ToMap) and puts you at its spot ToSpot; ToMap "" = the end of the built world */
struct FPBXExit { FString Id, Label, ToMap, ToSpot; FVector Pos = FVector::ZeroVector; float Radius = 250.f; int32 MinStep = 0; };
/** a sight-line trainer: challenges you when you walk into their view (until beaten) */
struct FPBXTrainer { FName Id; float Sight = 900.f; TArray<TPair<FName, int32>> Team; int32 Reward = 200; TArray<FString> Intro, Win, After; };
struct FPBXItem { FString Id, Item; int32 Count = 1; FVector Pos = FVector::ZeroVector; TWeakObjectPtr<AActor> Actor; };
struct FPBXLine { FName Who; FString Text; };
/** one camera move of a cutscene (phase 6): eye A0 -> A1 looking at L0 -> L1, eased, with an optional caption */
struct FPBXCutShot
{
	FVector A0, A1, L0, L1; float Dur = 4.f, Fov = 60.f; FString Caption, Sub;
	// Sigil & Spark intro (2026-10-31): narration (a sound under /Game/PBX/Audio, the shot lasts at least its length + .7 s),
	// a subtitle (+ speaker), the ink overlay mode (0 = the world) / its title, and a hook that runs when the shot starts
	FString Vo, Subtitle, SubSpeaker; int32 Ink = 0; FString InkTitle; TFunction<void()> OnStart;
};

UCLASS()
class APBXDirector : public AActor
{
	GENERATED_BODY()
public:
	APBXDirector();
	virtual void BeginPlay() override;
	virtual void Tick(float Dt) override;
	virtual void EndPlay(const EEndPlayReason::Type R) override;

	// ---- input (from the controller)
	void InMove(FVector2D V); void InLook(FVector2D V); void InJump(); void InConfirm(); void InBack(); void InPause(); void InConfirmMouse();
	void OpenHardPause(); void ResumeHardPause(); void PausePick(int32 i);
	void InRun(bool b); void InZoom(float D); void InNav(int32 Dx, int32 Dy); void InNumber(int32 N);
	bool WantsCursor() const;

private:
	// ---- data
	TSharedPtr<FJsonObject> Data;
	FPBXSpot NewGameSpot; TArray<FPBXDoor> Doors; TMap<FString, FPBXSpot> Spots; TArray<FBox2D> Grass; TArray<FVector> WildSpawns;
	FString MapName = TEXT("L_Town"), MapTitle, ChapterLabel;
	TArray<TArray<TPair<FName, int32>>> GrassPool; TArray<FIntPoint> GrassLv;     // per tall-grass patch: weighted Echo pool + level range
	TArray<FPBXExit> Exits; TArray<FVector2D> Corridor; float CorridorW = 0.f; bool bHasGate = false; bool bTraveling = false;
	TMap<FName, FPBXTrainer> Trainers; TArray<FPBXItem> Items; float ItemFxT = 0.f;
	int32 PatchOf(const FVector& P) const;
	FName PickWild(int32 Patch) const;
	bool IsTown() const { return MapName == TEXT("L_Town"); }
	FVector GatePos = FVector::ZeroVector; float GateExitX = 0.f; FVector2D BoundsCenter = FVector2D::ZeroVector; float BoundsRadius = 9000.f, WaterZ = -110.f; FPBXSpot SafeSpot;
	FVector StarterTable = FVector::ZeroVector, BedPos = FVector::ZeroVector;
	struct FSign { FVector Pos; FString Text; bool bWorldText = true; }; TArray<FSign> Signs;   // bWorldText false = a note / grave (read with E, no 3D lettering)
	TArray<TArray<FVector2D>> ExtraPaths; TArray<float> ExtraW;   // walkable corridors outside the bounds circle (the Lamplighters' Path)
	bool InExtra(const FVector& Q) const;
	// railway: the train at Lumen Station is the way out of town (chapter end)
	FPBXSpot TrainBoard, TrainCam; FVector TrainDir = FVector(0, 1, 0); float TrainExitY = 0.f; bool bHasTrain = false;
	bool bTrainGo = false; float TrainV = 0.f;
	bool LoadData();
	FPBXSpot ReadSpot(const TSharedPtr<FJsonObject>& O) const;

	// ---- world
	UPROPERTY() TObjectPtr<APBXPlayer> Player;
	UPROPERTY() TObjectPtr<APBXEcho> Partner;
	UPROPERTY() TMap<FName, TObjectPtr<APBXNPC>> NPCs;
	UPROPERTY() TArray<TObjectPtr<APBXEcho>> Wilds;
	UPROPERTY() TArray<TObjectPtr<AActor>> GateBarrier;
	UPROPERTY() TArray<TObjectPtr<AActor>> Train;
	void BoardTrain();
	void TickTrain(float Dt);
	UPROPERTY() TArray<TObjectPtr<AActor>> TableCards;   // Sigil & Spark: the three starter Sparks on the table
	UPROPERTY() TArray<TObjectPtr<UTexture2D>> CardTex;
	UPROPERTY() TObjectPtr<ACameraActor> Cam;
	UPROPERTY() TObjectPtr<UPBXGameSubsystem> Game;
	void SpawnWorld();
	void SpawnNPCs();
	void RefreshWorld();
	void SpawnPartner(bool bPop);
	void ApplyPlayerLook();
	void ArriveAt(const FString& SpotId);
	void Travel(const FString& ToMap, const FString& ToSpot);
	void ReachEnd(const FPBXExit& E);
	void TrainerSpotted(FName Id);
	void PickItem(int32 i);
	void HealTeam(FName Who);
	void OpenShop();
	void OpenTeam();
	void OpenMonActions(int32 i);
	int32 MonMaxHP(const FPBXMon& M) const;
	void PlacePlayer(const FPBXSpot& S);
	void UpdateWilds(float Dt);
	bool Inside() const;
	FVector PlayerLoc() const;
	UTexture2D* CardTexture(FName Card);

	// ---- UI
	TSharedPtr<FPBXUIModel> UI; TSharedPtr<SPBXHud> Hud;
	void Toast(const FString& T);
	void Splash(const FString& Title, const FString& Sub, float Secs = 2.6f);
	void UpdateObjective();
	void UpdatePrompt();
	FString SpeakerName(FName Who) const;

	// ---- script queue (dialogue, waits, fades...) — while it runs the player can't walk
	TArray<TFunction<bool(float)>> Queue; bool bConfirm = false; float StepT = 0.f; int32 QueueGen = 0;
	void Q(TFunction<bool(float)> F) { Queue.Add(MoveTemp(F)); }
	void QDo(TFunction<void()> F);
	void QWait(float S);
	void QSay(const TArray<FPBXLine>& Lines);
	void QFade(float To, float Secs = .35f);
	/** a skippable letterboxed cutscene in the script queue (confirm skips); AutoShot = screenshot name in the autotest */
	void QCut(const TArray<FPBXCutShot>& Shots, const FString& AutoShot = FString(), TFunction<void()> OnEnd = nullptr);
	/** the Sigil & Spark opening (SIGIL_AND_SPARK.md section 8): ink myth → Lumen Harbor at dawn → the White Page */
	void PlayIntro();
	/** Sigil & Spark (dark): the people the Blanking took — white, frozen, wordless (off during the intro's "before") */
	void ApplyBlanked(bool bOn);
	bool bIntroShip = false; float IntroShipT0 = 0.f;
	UPROPERTY() TArray<TObjectPtr<AActor>> IntroActors;
	// the drawn saga intro (Blender video, 2026-11-01): Content/Movies/saga_intro.mp4 + saga_intro_subs.json
	UPROPERTY() TObjectPtr<class UMediaPlayer> MoviePlayer;
	UPROPERTY() TObjectPtr<class UMediaTexture> MovieTex;
	UPROPERTY() TObjectPtr<class UMediaSoundComponent> MovieSound;
	UPROPERTY() TObjectPtr<class UFileMediaSource> MovieSrc;
	bool PlayIntroMovie(TFunction<void()> OnEnd);
	void CheckCutscenes();   // first visits: the lighthouse island, the Lamplighters' Rest
	bool Busy() const { return Queue.Num() > 0; }

	// ---- interactions
	enum class EKind : uint8 { None, NPC, Door, Bed, Table, Sign, Train, Item, Boat, Dock, Story };
	// the rowboat (2026-10-23): board it at the pier, steer with the move keys, step ashore at a dock
	struct FDock { FString Name; FVector Water = FVector::ZeroVector; FPBXSpot Land; };
	TArray<FDock> Docks; UPROPERTY() TObjectPtr<AActor> Boat; FVector BoatStart = FVector::ZeroVector; float BoatRadius = 260000.f;
	bool bBoating = false; FVector2D BoatXY = FVector2D::ZeroVector; float BoatYaw = 0.f, BoatSpeed = 0.f, BoatTurn = 0.f, BoatZOff = 0.f, BoatT = 0.f;
	FVector2D BoatInput = FVector2D::ZeroVector; TArray<TObjectPtr<AActor>> BoatIgnore;
	void BoardBoat(); void LeaveBoat(int32 Dock); void TickBoat(float Dt); float WaveZ(const FVector2D& XY, float T) const; float BoatGroundZ(const FVector2D& XY) const;
	// ---- the living harbour (2026-10-23 b): windmill sails turning in the wind, boats riding the swell (moored in the
	// harbour / anchored out in the bay / one sailing a loop round the bay), their crews attached on board
	struct FSail { TWeakObjectPtr<USceneComponent> C; float Rate = 25.f; };
	TArray<FSail> Sails;
	struct FSeaBoat
	{
		TWeakObjectPtr<AActor> A; int32 Mode = 0; FVector2D XY = FVector2D::ZeroVector, C = FVector2D::ZeroVector; float Yaw = 0.f, Z0 = 0.f, Phase = 0.f, Rx = 0.f, Ry = 0.f, Period = 300.f, Len = 400.f, Beam = 150.f;
		// 2026-10-31 hull dynamics: heave / pitch / roll chase the wave surface through damped springs (inertia, overshoot)
		float Hz = 0.f, Vz = 0.f, Pt = 0.f, Vp = 0.f, Ro = 0.f, Vr = 0.f; bool bDyn = false; float HalfLen = 200.f;
		// Mode 3 = a fishing boat's working day: berth → out to the grounds → fish → back → a crew member sells the catch
		int32 St = 0, PathI = 0, Sub = 0; float StT = 0.f, Wait = 60.f, Spd = 0.f, BerthYaw = 0.f, PierX = 0.f; TArray<FVector2D> Path;
		FVector2D Berth = FVector2D::ZeroVector, Ground = FVector2D::ZeroVector; TWeakObjectPtr<class APBXNPC> Seller; FVector SeatRel = FVector::ZeroVector; float SeatYaw = 0.f; int32 Trips = 0;
	};
	void TickFisher(FSeaBoat& B, float Dt, float T);
	bool SteerBoat(FSeaBoat& B, float Dt);
	/** sea state: 1 = normal; swell sets roll in every few minutes (the sea material reads it from MPC_PBX_Sea) */
	float Swell = 1.f;
	UPROPERTY() TObjectPtr<UObject> SeaMPC;
	FVector StallPos = FVector::ZeroVector;
	TArray<FSeaBoat> SeaBoats;
	void SetupLife(); void TickLife(float Dt);
	float PerfT = 0.f, PerfAcc = 0.f, PerfWorst = 0.f; int32 PerfN = 0;   // autotest frame-time log (RTX 2060 budget)
	/** the bay is calmer near the shore (the same factor scales the sea material's swell) */
	static float ShoreDamp(const FVector2D& XY);
	EKind NearKind = EKind::None; int32 NearIndex = -1; FName NearNPC;
	void FindNearest();
	void Interact();
	void TalkTo(APBXNPC* N);
	void UseDoor(const FPBXDoor& D, bool bFromOutside);
	void Rest();
	void ChooseStarter(bool bRite = false);
	/** r65 opening: the Rite of Pages night → the first fight → dawn (then Capture) */
	void BeginRite(); void StartFirstFight(); void DawnAfterRite(bool bWon);
	TArray<FPBXLine> LinesFor(FName Who) const;


	// ---- v3 story runtime (2026-11-06, the choice-driven pivot): Content/PBX/Story/<ep>.json scene graphs (PBXStory.cpp)
	TSharedPtr<FJsonObject> StoryData; FString StoryEp, StoryScene; bool bStoryMode = false;
	TMap<FString, int32> SVars;
	struct FStoryFrame { TArray<TSharedPtr<class FJsonValue>> Nodes; int32 I = 0; };
	TArray<FStoryFrame> SStack;
	struct FStorySpot { FString Id, Label; FVector Pos = FVector::ZeroVector; TArray<TSharedPtr<class FJsonValue>> Do; bool bOnce = true; };
	TArray<FStorySpot> HubSpots; bool bHub = false;
	TFunction<void()> OnFuse;
	UPROPERTY() TObjectPtr<UAudioComponent> StoryVoice;
	UPROPERTY() TObjectPtr<UAudioComponent> StoryMusic;
	UPROPERTY() TObjectPtr<UAudioComponent> StoryAmb;
	FString StoryMusicName, StoryAmbName;
	TMap<TWeakObjectPtr<AActor>, FTransform> NpcHome;   // where the story found each cast member it moved onto a stage
	void StoryLoop(TObjectPtr<UAudioComponent>& Comp, FString& Cur, const TCHAR* Kind, const FString& Name, float Vol, float Fade);
	void StoryAudioStop();
	float StoryVoicePlay(const FString& Id);
	// cinematic dialogue cameras (owner: "the talks cinematic, like we said"): a cut per line — over the shoulder, close-up,
	// two-shot — with a slow push-in; released when the player walks again
	TWeakObjectPtr<AActor> ShotOther; bool bStoryCam = false; FVector ShotA = FVector::ZeroVector, ShotB = FVector::ZeroVector, ShotLook = FVector::ZeroVector; float ShotT = 0.f, ShotFov = 40.f; int32 ShotN = 0; float ShotSide = 0.f; TWeakObjectPtr<AActor> ShotPairA, ShotPairB;
	void StoryShot(const FString& Who); void StoryCamRelease(); void StoryCamTick(float Dt); void StoryMarksTick();
	/** acting: the speaker gestures for the length of the line, the listener reacts; heads turn to whoever speaks */
	void StoryAct(const FString& Who, const FString& Line, float Secs); void StoryActTick();
	TWeakObjectPtr<APBXCharacterBase> ActSpk; double ActEnd = 0.0; int32 ActN = 0; double FaceShotAt = 0.0; FString FaceShotName; int32 FaceShots = 0;
	/** film mode (owner 2026-11-06 22:58): a pre-rendered clip per beat, Content/Movies/<ep>/<vo id>.mp4, played under the UI;
	    no clip = live staging. -pbxnofilm forces the live staging. */
	UPROPERTY() TObjectPtr<class UMediaPlayer> FilmPlayer;
	UPROPERTY() TObjectPtr<class UMediaTexture> FilmTex;
	UPROPERTY() TObjectPtr<class UFileMediaSource> FilmSrc;
	/** nearest spot to a stage point where a person fits ON THE FLOOR (not on a stall roof or a crate) */
	FVector StoryFloor(const FVector& Want, const AActor* Ignore = nullptr) const;
	bool StoryFilm(const FString& Id); void StoryFilmStop(); bool bFilmOn = false; int32 FilmPlayed = 0, FilmMissed = 0;
	/** film CAPTURE (owner 2026-11-08 22:11, "everything smooth, right rhythm, detail everywhere"): -pbxfilm[=name] plays the
	    story on the -pbxpath choices at a FIXED 30 fps game clock (run with -benchmark -fps=30), cinematic quality, and writes
	    every frame (no UI) to Saved/film/<name>/f_000000.png + cues.jsonl (voices, music, ambience, sfx, lines, choices with
	    their frame numbers) → tools/film/film_mux.py makes the mp4 with the sound. */
	bool bFilmCap = false, bFilmRec = false; int32 FilmFrame = 0; FString FilmDir; float StoryLineSecs = 0.f;
	void FilmCue(const FString& Kind, const FString& Id, float Vol = 1.f, const FString& Extra = FString()); void FilmCaptureTick();
	void OnFilmShot(int32 W, int32 Hh, const TArray<FColor>& Px); int32 FilmShotN = 0; TSharedPtr<std::atomic<int32>> FilmPending;
	AActor* StoryActor(const FString& Who) const; FVector HeadOf(AActor* A) const;
	void QCard(const FString& Text, const FString& Sub, const FString& Vo);
	FString StorySpeakerName, LastLine, AutoPath; FLinearColor StorySpeakerColor = FLinearColor(1, .82f, .2f); int32 AutoChoice = 0;
	bool HasStory(const FString& Ep) const;
	bool LoadStory(const FString& Ep);
	void StoryBegin(const FString& Ep, const FString& Scene, bool bFromSave);
	void StoryGoto(const FString& Scene);
	void StoryPump();
	void QStoryPump();
	void StoryPush(const TArray<TSharedPtr<class FJsonValue>>* Nodes);
	bool StoryCond(const FString& C) const;
	int32 SVar(const FString& K) const { const int32* V = SVars.Find(K); return V ? *V : 0; }
	FString StoryText(const FString& T) const;
	FString StorySpeaker(const FString& Who, FLinearColor& OutColor) const;
	FVector StoryAt(const FString& At) const;
	void StoryChoice(const TSharedPtr<FJsonObject>& N);
	void StoryFuseTick(float Dt);
	void StoryPact(const TSharedPtr<FJsonObject>& N);
	bool StoryHub(const TSharedPtr<FJsonObject>& N);   // true = its exit condition holds (move on)
	void StoryUseSpot(int32 i);
	void StoryEndEpisode();

	// ---- story
	EPBXStep Step() const;
	void SetStep(EPBXStep S);
	void StoryTick(float Dt);
	void CompleteChapter();
	FVector ObjectiveTarget(FString& OutLabel) const;
	FVector LastSafe = FVector::ZeroVector; float SafeT = 0.f; float WarnT = 0.f;

	// ---- battle
	struct FBattleCtx
	{
		bool bActive = false, bWild = false, bTrainer = false, bChoosing = false, bStory = false;
		FPBXBattle B; TWeakObjectPtr<APBXEcho> Foe; TWeakObjectPtr<APBXEcho> Mine; FVector A, Bp, D, Side; bool bOwnsFoe = false;
		FName Trainer; float CamS = 1.f; TArray<int32> MoveCodes; int32 FoeLv = 10; TArray<int32> PreHP[2]; int32 PreAct[2] = { 0, 0 };
		TWeakObjectPtr<AStaticMeshActor> Ball;
		FVector CamBase = FVector::ZeroVector; FRotator CamRot = FRotator::ZeroRotator; float Punch = 0.f, Clock = 0.f;   // cinematic camera
	} Bt;
	UPROPERTY() TObjectPtr<APBXFX> FX;
	bool ToScreen(const FVector& W, FVector2D& Out) const;
	void BattleBanner(const FString& T, FLinearColor C, float Secs = 1.2f);
	void HitFX(int32 TargetSide, const FPBXEvent& E);
	void StartWildBattle(APBXEcho* W);
	void StartTrainerBattle(FName Who);
	void SetupStage(const FVector& FoePos);
	// battle staging: hide small props / plants / other NPCs and wild Echoes that would cover the arena or the camera's view of it
	TArray<TWeakObjectPtr<AActor>> StageHidden;
	void ClearStage(const TArray<AActor*>& Keep);
	void RestoreStage();
	void ShowMoves();
	void PickMove(int32 i);
	void PlayEvents(const TArray<FPBXEvent>& Ev);
	TArray<FPBXEvent> DoRound(EPBXMove M, int32 To);
	void TryCapture();
	void EndBattle(const FString& Result);
	void SyncPlates();
	void Floater(const FVector& W, const FString& T, const FLinearColor& C);
	void SaveTeamHP();

	// ---- menus
	enum class EMenu : uint8 { None, Title, Gender, Pause, Controls, Complete, Confirm, Team, Settings, Look };
	// r65 hero looks: the same face in four skin tones (+ hair), previewed live after the gender pick
	bool bPendingMale = true; int32 PendingLook = 0;
	static FString LookId(bool bMale, int32 Look);
	void PreviewLook(int32 Look);
	// ---- settings (r65, user 2026-11-01: "settings and every menu option a game should have"): audio, display, camera,
	// subtitles; stored in GameUserSettings.ini [PBX.Settings] (display via UGameUserSettings)
	float VolMaster = 1.f, VolMusic = 1.f, VolSfx = 1.f, LookSens = 1.f; bool bInvertY = false, bSubs = true, bInkStyle = false;
	// the ink / Codex look over the whole world (user 2026-11-01): M_PBX_AnimePP (ink outlines, cel bands, hatching) on an unbound PP volume
	UPROPERTY() TObjectPtr<class UMaterialInstanceDynamic> InkMID;
	void ApplyInkStyle();
	// r66 (council 2026-11-06): ink strength presets 1..4 (0 = off) + a "mood" grade (darker, colder, film grain, fog)
	int32 InkPreset = 3; bool bMood = false; bool bStyle = false; int32 StyleIdx = -1, StylePh = 0; float StyleT = 0.f;   // owner 2026-11-06: preset 3 "Ink" + the darker mood
	struct FMoodBack { bool bSaved = false, bSun = false, bSky = false; float FogDensity = 0.f, SunI = 0.f, SkyI = 0.f; FLinearColor FogColor, SunC; } MoodBack;
	void ApplyMood(); void ApplyPerf(); void StyleTick(float Dt);
	EMenu SettingsBack = EMenu::Title;
	void LoadSettings(); void SaveSettings(); void ApplyAudioSettings();
	void AdjustSetting(int32 Row, int32 Dir);
	// the title screen's drawn background (a Blender loop, Content/Movies/title_loop.mp4) instead of the live town
	UPROPERTY() TObjectPtr<class UFileMediaSource> TitleSrc; bool bTitleLoop = false;
	void StartTitleLoop(); void StopTitleLoop();
	EMenu Menu = EMenu::None;
	void ShowMenu(EMenu M);
	void OpenChoice(const FString& Title, const FString& Sub, const TArray<FPBXOption>& Opts, bool bCards, TFunction<void(int32)> Pick);
	void CloseChoice();
	void StartNewGame(bool bMale);
	void ContinueGame();
	void SaveNow(bool bToast);
	void ToTitle();

	// ---- autoplay test (-pbxauto)
	bool bAuto = false; int32 AutoStep = 0; float AutoT = 0.f, AutoStepT = 0.f; int32 AutoShots = 0; bool bAutoFail = false;
	void AutoTick(float Dt);
	void Shot(const FString& Name);
	bool ShotFirst(const TCHAR* Name);   // true = shot requested, come back next tick; false = shot done, carry on
	void LogMHHeights();
	int32 ShotWait = 0; FString ShotPendingName, ShotDoneName;
	void AutoNext() { AutoStep++; AutoStepT = 0.f; }
	void TeleportPlayer(const FVector& P, float Yaw);
	// ---- audio (original chiptune, tools/chiptune.py -> /Game/PBX/Audio): one music track at a time + 2D sound effects
	UPROPERTY() TObjectPtr<UAudioComponent> MusicComp;
	UPROPERTY() TMap<FName, TObjectPtr<USoundBase>> SoundCache;
	FString MusicName; float MusicHold = 0.f;
	bool bWasInside = false; float OutdoorArm = 430.f;
	USoundBase* Snd(const TCHAR* Name);
	void Sfx(const TCHAR* Name, float Vol = 1.f);
	void Music(const TCHAR* Name);
	/** 2026-10-31 (phase 7): orchestral CC0 themes by place — home interior, village, harbour (on the water / by the
	 *  piers), the lighthouse island, Route 1 */
	const TCHAR* MapMusic() const;
	// fixed "player-truth" beauty cams (council 2026-10-16): same poses every run, guarded, captions in Saved/pbx_auto/beauty.txt
	int32 BeautyIdx = -1, BeautyPhase = 0; float BeautyT = 0.f; FPBXSpot BeautyBack; TArray<FString> BeautyDone;
	bool BeautyPass(float Dt);   // true once every cam of the current map has been shot
	float PlayTimeAcc = 0.f;
	bool bRunHeld = false;
};

UCLASS()
class APBXGameMode : public AGameModeBase
{
	GENERATED_BODY()
public:
	APBXGameMode();
	virtual void BeginPlay() override;
};

UCLASS()
class APBXController : public APlayerController
{
	GENERATED_BODY()
public:
	TWeakObjectPtr<APBXDirector> Director;
protected:
	virtual void SetupInputComponent() override;
	virtual void PlayerTick(float Dt) override;
private:
	UPROPERTY() TObjectPtr<UInputMappingContext> IMC;
	UPROPERTY() TArray<TObjectPtr<UInputAction>> Actions;
	UInputAction* MakeAction(FName N, bool bAxis2D, bool bAxis1D = false);
};
