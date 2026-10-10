#include "PBX/PBXDirector.h"
#include "PBX/PBXActors.h"
#include "PBX/PBXAnim.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/TextRenderComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/Texture2D.h"
#include "EngineUtils.h"
#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/SpringArmComponent.h"
#include "HighResScreenshot.h"
#include "ImageUtils.h"
#include "InputAction.h"
#include "InputMappingContext.h"
#include "InputModifiers.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Misc/FileHelper.h"
#include "Misc/App.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "UnrealClient.h"
#include "Blueprint/WidgetLayoutLibrary.h"
#include "Widgets/SWeakWidget.h"

DEFINE_LOG_CATEGORY_STATIC(LogPBX, Log, All);
#define PBXLOG(Fmt, ...) UE_LOG(LogPBX, Display, TEXT(Fmt), ##__VA_ARGS__)

static FVector JVec(const TSharedPtr<FJsonObject>& O, const TCHAR* Key)
{
	const TArray<TSharedPtr<FJsonValue>>* A; if (!O.IsValid() || !O->TryGetArrayField(Key, A) || A->Num() < 2) return FVector::ZeroVector;
	return FVector((*A)[0]->AsNumber(), (*A)[1]->AsNumber(), A->Num() > 2 ? (*A)[2]->AsNumber() : 0.0);
}
static FVector JVecV(const TSharedPtr<FJsonValue>& V)
{
	const TArray<TSharedPtr<FJsonValue>>& A = V->AsArray(); return FVector(A[0]->AsNumber(), A[1]->AsNumber(), A.Num() > 2 ? A[2]->AsNumber() : 0.0);
}

APBXDirector::APBXDirector() { PrimaryActorTick.bCanEverTick = true; PrimaryActorTick.TickGroup = TG_PostPhysics; }

// =================================================================== data
FPBXSpot APBXDirector::ReadSpot(const TSharedPtr<FJsonObject>& O) const
{
	FPBXSpot S; if (!O.IsValid()) return S; S.Pos = JVec(O, TEXT("pos")); S.Yaw = O->GetNumberField(TEXT("yaw")); return S;
}

bool APBXDirector::LoadData()
{
	const FString Map = GetWorld()->GetMapName().Replace(*GetWorld()->StreamingLevelsPrefix, TEXT(""));
	const FString Path = FPaths::ProjectContentDir() / TEXT("PBX/Data") / (Map + TEXT(".json"));
	FString Txt; if (!FFileHelper::LoadFileToString(Txt, *Path)) { PBXLOG("[PBX] no map data %s", *Path); return false; }
	TSharedRef<TJsonReader<>> R = TJsonReaderFactory<>::Create(Txt);
	if (!FJsonSerializer::Deserialize(R, Data) || !Data.IsValid()) { PBXLOG("[PBX] bad json %s", *Path); return false; }
	NewGameSpot = ReadSpot(Data->GetObjectField(TEXT("new_game")));
	for (const TSharedPtr<FJsonValue>& V : Data->GetArrayField(TEXT("doors")))
	{
		const TSharedPtr<FJsonObject> O = V->AsObject(); FPBXDoor D;
		D.Id = O->GetStringField(TEXT("id")); D.Label = O->GetStringField(TEXT("label")); O->TryGetBoolField(TEXT("locked"), D.bLocked);
		if (O->HasField(TEXT("outside"))) D.Outside = ReadSpot(O->GetObjectField(TEXT("outside")));
		if (O->HasField(TEXT("inside"))) D.Inside = ReadSpot(O->GetObjectField(TEXT("inside")));
		D.OutDoor = JVec(O, TEXT("out_door")); D.InDoor = JVec(O, TEXT("in_door"));
		Doors.Add(D);
	}
	const TSharedPtr<FJsonObject> Sp = Data->GetObjectField(TEXT("spots"));
	for (const auto& KV : Sp->Values)
	{
		if (KV.Value->Type == EJson::Object) Spots.Add(FString(KV.Key), ReadSpot(KV.Value->AsObject()));
		else { FPBXSpot S; S.Pos = JVecV(KV.Value); Spots.Add(FString(KV.Key), S); }
	}
	StarterTable = Spots.Contains(TEXT("starter_table")) ? Spots[TEXT("starter_table")].Pos : FVector::ZeroVector;
	BedPos = Spots.Contains(TEXT("bed")) ? Spots[TEXT("bed")].Pos : FVector::ZeroVector;
	for (const TSharedPtr<FJsonValue>& V : Data->GetArrayField(TEXT("grass")))
	{
		const FVector Mn = JVec(V->AsObject(), TEXT("min")), Mx = JVec(V->AsObject(), TEXT("max"));
		Grass.Add(FBox2D(FVector2D(FMath::Min(Mn.X, Mx.X), FMath::Min(Mn.Y, Mx.Y)), FVector2D(FMath::Max(Mn.X, Mx.X), FMath::Max(Mn.Y, Mx.Y))));
	}
	for (const TSharedPtr<FJsonValue>& V : Data->GetArrayField(TEXT("wild_spawns"))) WildSpawns.Add(JVecV(V));
	const TSharedPtr<FJsonObject> G = Data->GetObjectField(TEXT("gate")); GatePos = JVec(G, TEXT("pos")); GateExitX = G->GetNumberField(TEXT("exit_x"));
	const TSharedPtr<FJsonObject> Bd = Data->GetObjectField(TEXT("bounds"));
	const FVector C = JVec(Bd, TEXT("center")); BoundsCenter = FVector2D(C.X, C.Y); BoundsRadius = Bd->GetNumberField(TEXT("radius")); WaterZ = Bd->GetNumberField(TEXT("water_z"));
	SafeSpot = ReadSpot(Bd->GetObjectField(TEXT("safe")));
	for (const TSharedPtr<FJsonValue>& V : Data->GetArrayField(TEXT("signs")))
		Signs.Add({ JVec(V->AsObject(), TEXT("pos")), V->AsObject()->GetStringField(TEXT("text")) });
	const TSharedPtr<FJsonObject>* Tr = nullptr;
	if (Data->TryGetObjectField(TEXT("train"), Tr))
	{
		bHasTrain = true; TrainBoard = ReadSpot((*Tr)->GetObjectField(TEXT("board"))); TrainCam = ReadSpot((*Tr)->GetObjectField(TEXT("cam")));
		TrainDir = JVec(*Tr, TEXT("dir")).GetSafeNormal(); TrainExitY = (*Tr)->GetNumberField(TEXT("exit_y"));
	}
	return true;
}

// =================================================================== lifecycle
void APBXDirector::BeginPlay()
{
	Super::BeginPlay();
	bAuto = FParse::Param(FCommandLine::Get(), TEXT("pbxauto"));
	if (GEngine) { GEngine->bEnableOnScreenDebugMessages = false; GEngine->Exec(GetWorld(), TEXT("DisableAllScreenMessages")); }
	Game = GetGameInstance()->GetSubsystem<UPBXGameSubsystem>();
	UI = MakeShared<FPBXUIModel>();
	if (GEngine && GEngine->GameViewport)
	{
		Hud = SNew(SPBXHud, UI);
		GEngine->GameViewport->AddViewportWidgetContent(SNew(SWeakWidget).PossiblyNullContent(Hud.ToSharedRef()), 10);
	}
	if (!LoadData()) { Toast(TEXT("Map data missing — rebuild the town (blender_town.py).")); }
	SpawnWorld();
	if (APBXController* PC = Cast<APBXController>(GetWorld()->GetFirstPlayerController())) PC->Director = this;
	ShowMenu(EMenu::Title);
	PBXLOG("[PBX] director ready (auto=%d)", bAuto);
}

void APBXDirector::EndPlay(const EEndPlayReason::Type R)
{
	if (Hud.IsValid() && GEngine && GEngine->GameViewport) GEngine->GameViewport->RemoveAllViewportWidgets();
	Super::EndPlay(R);
}

FVector APBXDirector::PlayerLoc() const { return Player ? Player->GetActorLocation() : FVector::ZeroVector; }
bool APBXDirector::Inside() const { return Player && Player->GetActorLocation().Z < -3000.f; }

UTexture2D* APBXDirector::CardTexture(FName Card)
{
	const FPBXCardDef* C = PBXData::Card(Card); if (!C) return nullptr;
	for (UTexture2D* T : CardTex) if (T && T->GetFName() == Card) return T;
	UTexture2D* T = FImageUtils::ImportFileAsTexture2D(C->CardImagePath());
	if (T) { T->Rename(*Card.ToString(), GetTransientPackage()); CardTex.Add(T); }
	else PBXLOG("[PBX] card image missing: %s", *C->CardImagePath());
	return T;
}

void APBXDirector::SpawnWorld()
{
	UWorld* W = GetWorld();
	Player = Cast<APBXPlayer>(UGameplayStatics::GetPlayerPawn(this, 0));
	Cam = W->SpawnActor<ACameraActor>(FVector(4200, -3400, 2000), FRotator(-24, 140, 0));
	if (Cam) { Cam->GetCameraComponent()->SetFieldOfView(70.f); Cam->GetCameraComponent()->bConstrainAspectRatio = false; }
	for (TActorIterator<AActor> It(W); It; ++It)
	{
		if (It->ActorHasTag(TEXT("PBX_GateBarrier"))) GateBarrier.Add(*It);
		if (It->ActorHasTag(TEXT("PBX_Train"))) { Train.Add(*It); It->GetRootComponent()->SetMobility(EComponentMobility::Movable); }
	}
	SpawnNPCs();
	// readable signs (comic lettering on both faces of the board)
	for (int32 i = 0; i < Signs.Num(); i++)
	{
		const FSign& S = Signs[i];
		const float Yaw = Data->GetArrayField(TEXT("signs"))[i]->AsObject()->GetNumberField(TEXT("yaw"));
		AActor* A = W->SpawnActor<AActor>(AActor::StaticClass(), FTransform(S.Pos));
		if (!A) continue;
		USceneComponent* R = NewObject<USceneComponent>(A); A->SetRootComponent(R); R->RegisterComponent(); R->SetWorldLocation(S.Pos);
		for (int32 k = 0; k < 2; k++)
		{
			UTextRenderComponent* T = NewObject<UTextRenderComponent>(A); T->SetupAttachment(R); T->RegisterComponent();
			const float Y = Yaw + (k ? 180.f : 0.f); const FVector Fwd = FRotator(0, Y, 0).Vector();
			T->SetWorldLocationAndRotation(S.Pos + Fwd * 9.f, FRotator(0, Y, 0));
			T->SetText(FText::FromString(S.Text)); T->SetHorizontalAlignment(EHTA_Center); T->SetVerticalAlignment(EVRTA_TextCenter);
			T->SetWorldSize(17.f); T->SetTextRenderColor(FColor(40, 28, 20)); T->SetCastShadow(false);
		}
	}
	// the three cards on Dr. Vale's table
	TArray<FName> St = PBXData::Starters();
	UStaticMesh* CardMesh = LoadObject<UStaticMesh>(nullptr, TEXT("/Game/PBX/Meshes/SM_EchoCard.SM_EchoCard"));
	UMaterialInterface* Mat = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/PBX/Materials/M_PBX_Echo.M_PBX_Echo"));
	for (int32 i = 0; i < St.Num() && CardMesh && Mat; i++)
	{
		const FVector P = StarterTable + FVector((i - 1) * 70.f, 0, 0);
		AStaticMeshActor* A = W->SpawnActor<AStaticMeshActor>(P, FRotator(0, 90, 0));
		if (!A) continue;
		A->SetMobility(EComponentMobility::Movable);
		A->GetStaticMeshComponent()->SetStaticMesh(CardMesh); A->GetStaticMeshComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		A->SetActorScale3D(FVector(.42f, .42f * .716f, .42f));   // card aspect 63 x 88
		UMaterialInstanceDynamic* MID = UMaterialInstanceDynamic::Create(Mat, A);
		if (UTexture2D* T = CardTexture(St[i])) MID->SetTextureParameterValue(TEXT("Tex"), T);
		A->GetStaticMeshComponent()->SetMaterial(0, MID);
		A->SetActorRotation(FRotator(0, 90, -12));
		TableCards.Add(A);
	}
}

void APBXDirector::SpawnNPCs()
{
	if (!Data.IsValid()) return;
	UWorld* W = GetWorld();
	for (const TSharedPtr<FJsonValue>& V : Data->GetArrayField(TEXT("npcs")))
	{
		const TSharedPtr<FJsonObject> O = V->AsObject();
		const FVector P = JVec(O, TEXT("pos")); const float Yaw = O->GetNumberField(TEXT("yaw"));
		const float Z = PBXWorld::GroundZ(W, P, 300.f, 1500.f, P.Z);
		double Scale = 1.0; O->TryGetNumberField(TEXT("scale"), Scale);
		FActorSpawnParameters SP; SP.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButAlwaysSpawn;
		APBXNPC* N = W->SpawnActor<APBXNPC>(APBXNPC::StaticClass(), FVector(P.X, P.Y, Z + 92.f * Scale), FRotator(0, Yaw, 0), SP);
		if (!N) continue;
		N->Id = FName(*O->GetStringField(TEXT("id"))); N->DisplayName = O->GetStringField(TEXT("name"));
		FString Outfit; O->TryGetStringField(TEXT("outfit"), Outfit);
		const TArray<TSharedPtr<FJsonValue>>* HC = nullptr; FLinearColor HairC(0, 0, 0, 0);
		if (O->TryGetArrayField(TEXT("hair_color"), HC) && HC->Num() >= 3) HairC = FLinearColor((*HC)[0]->AsNumber(), (*HC)[1]->AsNumber(), (*HC)[2]->AsNumber(), 1.f);
		N->ApplyLook(O->GetStringField(TEXT("body")), O->GetStringField(TEXT("hair")), Scale, Outfit, HairC);
		N->IdleAnim = O->GetStringField(TEXT("anim")); N->Home = N->GetActorLocation(); N->HomeYaw = Yaw;
		N->ReturnToIdle();
		NPCs.Add(N->Id, N);
	}
}

void APBXDirector::SpawnPartner(bool bPop)
{
	if (!Game->HasPartner() || !Player) return;
	const FName Card = Game->State->Team[0].Card;
	if (Partner && Partner->CardId != Card) { Partner->Destroy(); Partner = nullptr; }
	if (!Partner)
	{
		const FVector P = PlayerLoc() - Player->GetActorForwardVector() * 130.f + Player->GetActorRightVector() * 95.f;
		Partner = GetWorld()->SpawnActor<APBXEcho>(APBXEcho::StaticClass(), FTransform(P));
		if (!Partner) return;
		const FPBXCardDef* C = PBXData::Card(Card);
		Partner->Setup(Card, 95.f * (C ? C->Size : 1.f)); Partner->PlaceAt(P);
	}
	Partner->Mode = APBXEcho::EMode::Follow; Partner->FollowTarget = Player; Partner->SetFaint(false);
	if (bPop) { Partner->PopIn(); Partner->Flash(FLinearColor(1, .95f, .7f), 4.f); }
}

void APBXDirector::PlacePlayer(const FPBXSpot& S)
{
	if (!Player) return;
	const float Z = PBXWorld::GroundZ(GetWorld(), S.Pos, 200.f, 1200.f, S.Pos.Z);
	Player->SetActorLocationAndRotation(FVector(S.Pos.X, S.Pos.Y, Z + 95.f), FRotator(0, S.Yaw, 0), false, nullptr, ETeleportType::TeleportPhysics);
	Player->GetCharacterMovement()->StopMovementImmediately();
	if (APlayerController* PC = GetWorld()->GetFirstPlayerController()) PC->SetControlRotation(FRotator(-12, S.Yaw, 0));
	LastSafe = Player->GetActorLocation();
}

void APBXDirector::TeleportPlayer(const FVector& P, float Yaw) { FPBXSpot S; S.Pos = P; S.Yaw = Yaw; PlacePlayer(S); }

// =================================================================== UI helpers
void APBXDirector::Toast(const FString& T) { FPBXUIModel::FToast X; X.Text = T; UI->Toasts.Add(X); if (UI->Toasts.Num() > 3) UI->Toasts.RemoveAt(0); PBXLOG("[PBX] toast: %s", *T); }
void APBXDirector::Splash(const FString& T, const FString& S, float Secs) { UI->BigTitle = T; UI->BigSub = S; UI->BigT = Secs; }

FString APBXDirector::SpeakerName(FName Who) const
{
	if (Who == TEXT("you")) return TEXT("You");
	if (Who == TEXT("note")) return TEXT("Note");
	if (const TObjectPtr<APBXNPC>* N = NPCs.Find(Who)) return (*N)->DisplayName;
	return Who.ToString();
}

void APBXDirector::QDo(TFunction<void()> F) { Q([F](float) { F(); return true; }); }
void APBXDirector::QWait(float S) { Q([S](float T) { return T >= S; }); }
void APBXDirector::QFade(float To, float Secs)
{
	TSharedPtr<float> From = MakeShared<float>(-1.f);
	Q([this, To, Secs, From](float T) { if (*From < 0.f) *From = UI->Fade; UI->Fade = FMath::Lerp(*From, To, FMath::Clamp(T / Secs, 0.f, 1.f)); return T >= Secs; });
}
void APBXDirector::QSay(const TArray<FPBXLine>& Lines)
{
	for (const FPBXLine& L : Lines)
	{
		Q([this, L](float T)
		{
			if (T == 0.f || UI->Mode != EPBXUIMode::Dialogue || UI->Line != L.Text)
			{
				UI->Mode = EPBXUIMode::Dialogue; UI->Speaker = SpeakerName(L.Who); UI->Line = L.Text; UI->Visible = 0.f; bConfirm = false;
				UI->SpeakerColor = L.Who == TEXT("rho") ? FLinearColor(.4f, .75f, 1.f) : FLinearColor(1, .82f, .2f);
				PBXLOG("[PBX] say %s: %s", *UI->Speaker, *L.Text);
			}
			UI->Visible = FMath::Min<float>(UI->Line.Len(), UI->Visible + FApp::GetDeltaTime() * 60.f);
			if (bAuto && UI->Visible >= UI->Line.Len() && T > .25f + UI->Line.Len() / 60.f) bConfirm = true;
			if (bConfirm)
			{
				bConfirm = false;
				if (UI->Visible < UI->Line.Len()) { UI->Visible = UI->Line.Len(); return false; }
				UI->Mode = EPBXUIMode::Explore; return true;
			}
			return false;
		});
	}
}

// =================================================================== tick
void APBXDirector::Tick(float Dt)
{
	Super::Tick(Dt);
	if (!UI.IsValid()) return;
	TickTrain(Dt);
	// script queue
	if (Queue.Num())
	{
		TFunction<bool(float)> F = Queue[0]; const int32 Gen = QueueGen;
		const bool bDone = F(StepT);
		StepT += Dt;
		if (bDone && Gen == QueueGen && Queue.Num()) { Queue.RemoveAt(0); StepT = 0.f; }
	}
	// UI timers
	for (int32 i = UI->Toasts.Num() - 1; i >= 0; i--) { UI->Toasts[i].T += Dt; if (UI->Toasts[i].T > 4.f) UI->Toasts.RemoveAt(i); }
	UI->BigT = FMath::Max(0.f, UI->BigT - Dt); UI->BannerT = FMath::Max(0.f, UI->BannerT - Dt); UI->ShakeT = FMath::Max(0.f, UI->ShakeT - Dt);
	APlayerController* PC = GetWorld()->GetFirstPlayerController();
	const float Scale = FMath::Max(.1f, UWidgetLayoutLibrary::GetViewportScale(this));
	for (FPBXFloater& F : UI->Floaters)
	{
		if (F.T > 2.f) continue;
		F.T += Dt; FVector2D S;
		if (PC && PC->ProjectWorldLocationToScreen(F.World + FVector(0, 0, 60.f + 90.f * F.T), S)) F.Screen = S / Scale - FVector2D(180, 45);
		F.Scale = F.T < .15f ? FMath::Lerp(1.8f, 1.f, F.T / .15f) : 1.f;
	}
	for (int32 s = 0; s < 2; s++) { FPBXPlate& P = UI->Plate[s]; if (P.ShownHP < 0.f) P.ShownHP = P.HP; P.ShownHP = FMath::FInterpConstantTo(P.ShownHP, P.HP, Dt, FMath::Max(20.f, P.MaxHP * 1.2f)); }
	if (Game && Game->State && UI->Mode != EPBXUIMode::Menu) { Game->State->PlayTime += Dt; }

	if (Player && Menu == EMenu::None && !Bt.bActive)
	{
		if (!Busy() && UI->Mode != EPBXUIMode::Choice) { UI->Mode = EPBXUIMode::Explore; FindNearest(); UpdatePrompt(); StoryTick(Dt); UpdateWilds(Dt); }
		UpdateObjective();
	}
	if (Game && Game->HasPartner())
	{
		const FPBXMon& M = Game->State->Team[0]; const FPBXCardDef* C = PBXData::Card(M.Card);
		UI->Partner.bShow = C != nullptr; if (C) { UI->Partner.Name = C->Name; UI->Partner.Lv = M.Lv; UI->Partner.MaxHP = FMath::RoundToInt(C->HP * PBXData::LvMult(M.Lv)); UI->Partner.HP = M.HP < 0 ? UI->Partner.MaxHP : M.HP; }
	}
	else UI->Partner.bShow = false;
	if (bAuto) AutoTick(Dt);
}

// =================================================================== input
bool APBXDirector::WantsCursor() const { return Menu != EMenu::None || UI->Mode == EPBXUIMode::Choice || (Bt.bActive && UI->bMoves); }

void APBXDirector::InMove(FVector2D V)
{
	if (!Player || Busy() || Menu != EMenu::None || Bt.bActive || UI->Mode == EPBXUIMode::Choice) return;
	const FRotator R(0, Player->GetControlRotation().Yaw, 0);
	Player->AddMovementInput(FRotationMatrix(R).GetUnitAxis(EAxis::X), V.Y);
	Player->AddMovementInput(FRotationMatrix(R).GetUnitAxis(EAxis::Y), V.X);
}
void APBXDirector::InLook(FVector2D V)
{
	if (!Player || Menu != EMenu::None || Bt.bActive) return;
	Player->AddControllerYawInput(V.X); Player->AddControllerPitchInput(V.Y);
}
void APBXDirector::InJump() { if (Player && !Busy() && Menu == EMenu::None && !Bt.bActive && UI->Mode == EPBXUIMode::Explore) Player->Jump(); }
void APBXDirector::InRun(bool b) { bRunHeld = b; if (Player) Player->SetRunning(b); }
void APBXDirector::InZoom(float D) { if (Player && Menu == EMenu::None && !Bt.bActive) Player->Zoom(D); }

void APBXDirector::InConfirm()
{
	if (UI->Mode == EPBXUIMode::Choice || Menu != EMenu::None)
	{
		if (UI->OnPick && UI->Options.IsValidIndex(UI->Selected) && UI->Options[UI->Selected].bEnabled) { TFunction<void(int32)> F = UI->OnPick; F(UI->Selected); }
		return;
	}
	if (Bt.bActive) { if (UI->bMoves) PickMove(UI->MoveSel); else bConfirm = true; return; }
	if (Busy()) { bConfirm = true; return; }
	if (NearKind != EKind::None) Interact(); else if (Player) Player->Jump();
}
void APBXDirector::InBack()
{
	if (Menu == EMenu::Pause || Menu == EMenu::Controls) { CloseChoice(); Menu = EMenu::None; return; }
}
void APBXDirector::InPause()
{
	if (Menu == EMenu::Pause || Menu == EMenu::Controls) { CloseChoice(); Menu = EMenu::None; return; }
	if (Menu == EMenu::None && !Busy() && !Bt.bActive && UI->Mode == EPBXUIMode::Explore) ShowMenu(EMenu::Pause);
}
void APBXDirector::InNav(int32 Dx, int32 Dy)
{
	if (UI->Mode == EPBXUIMode::Choice || Menu != EMenu::None)
	{
		const int32 N = UI->Options.Num(); if (!N) return;
		const int32 D = UI->bCards ? Dx : -Dy; if (!D) return;
		for (int32 k = 0; k < N; k++) { UI->Selected = (UI->Selected + D + N) % N; if (UI->Options[UI->Selected].bEnabled) break; }
	}
	else if (Bt.bActive && UI->bMoves)
	{
		const int32 N = UI->Moves.Num(); if (!N) return;
		int32 S = UI->MoveSel + Dx + (-Dy) * 2; S = (S % N + N) % N; UI->MoveSel = S;
	}
}
void APBXDirector::InNumber(int32 N)
{
	if (Bt.bActive && UI->bMoves && UI->Moves.IsValidIndex(N - 1)) { UI->MoveSel = N - 1; PickMove(N - 1); }
	else if ((UI->Mode == EPBXUIMode::Choice || Menu != EMenu::None) && UI->Options.IsValidIndex(N - 1)) { UI->Selected = N - 1; InConfirm(); }
}

// =================================================================== interactions
void APBXDirector::FindNearest()
{
	NearKind = EKind::None; NearIndex = -1; NearNPC = NAME_None;
	if (!Player) return;
	const FVector P = PlayerLoc(); float Best = 1e9f;
	auto Try = [&](const FVector& At, float R, EKind K, int32 I, FName N)
	{
		const float D = FVector::Dist2D(P, At); if (D < R && D < Best && FMath::Abs(P.Z - At.Z) < 400.f) { Best = D; NearKind = K; NearIndex = I; NearNPC = N; }
	};
	for (const auto& KV : NPCs) if (KV.Value && !KV.Value->IsHidden()) Try(KV.Value->GetActorLocation(), 230.f, EKind::NPC, -1, KV.Key);
	for (int32 i = 0; i < Doors.Num(); i++)
	{
		Try(Doors[i].OutDoor, 200.f, EKind::Door, i * 2, NAME_None);
		if (!Doors[i].bLocked) Try(Doors[i].InDoor, 200.f, EKind::Door, i * 2 + 1, NAME_None);
	}
	if (!BedPos.IsZero()) Try(BedPos, 210.f, EKind::Bed, 0, NAME_None);
	if (Step() == EPBXStep::Starter && !StarterTable.IsZero()) Try(StarterTable, 260.f, EKind::Table, 0, NAME_None);
	for (int32 i = 0; i < Signs.Num(); i++) Try(Signs[i].Pos, 230.f, EKind::Sign, i, NAME_None);
	if (bHasTrain && !bTrainGo) Try(TrainBoard.Pos, 320.f, EKind::Train, 0, NAME_None);
}

void APBXDirector::UpdatePrompt()
{
	FString T;
	switch (NearKind)
	{
	case EKind::NPC: T = FString::Printf(TEXT("[E]  Talk to %s"), *SpeakerName(NearNPC)); break;
	case EKind::Door: { const FPBXDoor& D = Doors[NearIndex / 2]; T = NearIndex % 2 ? TEXT("[E]  Go outside") : D.bLocked ? FString::Printf(TEXT("[E]  %s"), *D.Label) : FString::Printf(TEXT("[E]  Enter %s"), *D.Label); break; }
	case EKind::Bed: T = TEXT("[E]  Rest (heal your team & save)"); break;
	case EKind::Table: T = TEXT("[E]  Look at Dr. Vale's cards"); break;
	case EKind::Sign: T = TEXT("[E]  Read the sign"); break;
	case EKind::Train: T = Step() >= EPBXStep::Gate ? TEXT("[E]  Board the train to Mistvale") : TEXT("[E]  Look at the train"); break;
	default: break;
	}
	UI->Prompt = T;
}

void APBXDirector::Interact()
{
	switch (NearKind)
	{
	case EKind::NPC: if (TObjectPtr<APBXNPC>* N = NPCs.Find(NearNPC)) TalkTo(*N); break;
	case EKind::Door: UseDoor(Doors[NearIndex / 2], NearIndex % 2 == 0); break;
	case EKind::Bed: Rest(); break;
	case EKind::Table: if (TObjectPtr<APBXNPC>* V = NPCs.Find(TEXT("vale"))) TalkTo(*V); break;
	case EKind::Sign: QSay({ { TEXT("note"), Signs[NearIndex].Text.Replace(TEXT("\n"), TEXT(" — ")) } }); break;
	case EKind::Train:
		if (Step() >= EPBXStep::Gate) BoardTrain();
		else QSay({ { TEXT("conductor"), TEXT("The 10:15 to Mistvale, love. Rangers ride free — once Dr. Vale signs your licence.") } });
		break;
	default: break;
	}
}

void APBXDirector::UseDoor(const FPBXDoor& D, bool bFromOutside)
{
	if (bFromOutside && D.bLocked) { QSay({ { TEXT("note"), TEXT("Rho's house. The door is locked. A scribbled note says: \"Out delivering. Or napping.\"") } }); return; }
	const FPBXSpot To = bFromOutside ? D.Inside : D.Outside;
	QFade(1.f, .3f);
	QDo([this, To] { PlacePlayer(To); if (Partner) Partner->PlaceAt(To.Pos - FRotator(0, To.Yaw, 0).Vector() * 120.f); });
	QWait(.15f);
	QFade(0.f, .35f);
	if (!bFromOutside && D.Id == TEXT("house") && Step() == EPBXStep::WakeUp) QDo([this] { SetStep(EPBXStep::MeetRho); });
}

void APBXDirector::TalkTo(APBXNPC* N)
{
	if (!N) return;
	const FName Id = N->Id;
	Player->FaceTowards(N->GetActorLocation(), false); N->FaceTowards(PlayerLoc(), false);
	N->PlayAction(TEXT("Idle_Talking_Loop"), true, .3f);
	const EPBXStep S = Step();
	TArray<FPBXLine> L = LinesFor(Id);
	QSay(L);
	if (Id == TEXT("vale") && (S == EPBXStep::GoLab || S == EPBXStep::Starter))
	{
		QDo([this, N] { N->ReturnToIdle(); SetStep(EPBXStep::Starter); ChooseStarter(); });
		return;
	}
	if (Id == TEXT("rho") && S == EPBXStep::RhoBattle)
	{
		QDo([this, N] { N->ReturnToIdle(); StartTrainerBattle(TEXT("rho")); });
		return;
	}
	QDo([N] { N->ReturnToIdle(); });
}

void APBXDirector::Rest()
{
	QFade(1.f, .5f);
	QDo([this] { Game->HealAll(); if (Partner) Partner->SetFaint(false); });
	QWait(.6f);
	QFade(0.f, .5f);
	QDo([this] { SaveNow(false); Toast(TEXT("Your team is fully rested. Game saved.")); });
	if (Step() == EPBXStep::Rest)
	{
		QSay({ { TEXT("mom"), TEXT("Oh! A letter came for you while you slept. It's from Dr. Vale.") },
			   { TEXT("note"), TEXT("\"Ranger — Rho told me everything. Your licence is signed! The landslide still blocks Route 1, so take the train from Lumen Station to Mistvale.\"") },
			   { TEXT("mom"), TEXT("Your first real journey... Take care out there. And call your mother!") } });
		QDo([this] { SetStep(EPBXStep::Gate); Splash(TEXT("LICENCE SIGNED"), TEXT("Catch the train at Lumen Station")); SaveNow(false); });
	}
}

void APBXDirector::ChooseStarter()
{
	TArray<FPBXOption> Opts;
	for (FName Id : PBXData::Starters())
	{
		const FPBXCardDef* C = PBXData::Card(Id); FPBXOption O; O.Title = C->Name;
		O.Sub = FString::Printf(TEXT("%s type · %s"), *C->Type, *FPBXBattle::SigOf(C->Type).Name); O.Color = PBXData::TypeColor(C->Type);
		if (UTexture2D* T = CardTexture(Id)) O.Image = PBXUI::TextureBrush(T, FVector2D(250, 349));
		Opts.Add(O);
	}
	OpenChoice(TEXT("Choose your partner"), TEXT("Dr. Vale's three blank-stock cards. Your partner's Echo walks with you."), Opts, true, [this](int32 i)
	{
		const FName Id = PBXData::Starters()[i]; const FPBXCardDef* C = PBXData::Card(Id);
		CloseChoice();
		Game->AddMon(Id, PBXData::StartLevel(*C));
		if (TableCards.IsValidIndex(i) && TableCards[i]) TableCards[i]->SetActorHiddenInGame(true);
		SpawnPartner(true);
		Splash(C->Name.ToUpper(), TEXT("is your partner!"));
		QWait(1.2f);
		QSay({ { TEXT("vale"), FString::Printf(TEXT("%s! A splendid choice. Its Echo already trusts you."), *C->Name) },
			   { TEXT("vale"), TEXT("Wild Echoes gather in the tall grass by the west road. Weaken one in battle, then throw a Poké Ball to bind it to a blank Lattice card.") },
			   { TEXT("vale"), TEXT("Catch your first one, Ranger. Then come back and tell me all about it!") } });
		QDo([this] { SetStep(EPBXStep::Capture); SaveNow(false); });
	});
}

TArray<FPBXLine> APBXDirector::LinesFor(FName Who) const
{
	const EPBXStep S = Step(); const bool P = Game && Game->HasPartner();
	const FString PName = P ? PBXData::Card(Game->State->Team[0].Card)->Name : FString();
	if (Who == TEXT("mom"))
	{
		if (S <= EPBXStep::MeetRho) return { { Who, TEXT("Morning, sleepyhead! Today's the day — your Ranger licence!") }, { Who, TEXT("Dr. Vale is expecting you at Pokébox Labs. The big building with the satellite dish, at the end of the main road.") } };
		if (S == EPBXStep::Rest) return { { Who, TEXT("You look exhausted! Have a lie-down in your bed — it fixes everything.") } };
		if (P) return { { Who, FString::Printf(TEXT("%s is adorable! Make sure it eats properly. Echoes eat, right?"), *PName) } };
		return { { Who, TEXT("Go on, Dr. Vale is waiting!") } };
	}
	if (Who == TEXT("rho"))
	{
		switch (S)
		{
		case EPBXStep::WakeUp: case EPBXStep::MeetRho: case EPBXStep::GoLab: case EPBXStep::Starter: return { { Who, TEXT("Get your partner from Dr. Vale first. Then you and me — rival battle!") } };
		case EPBXStep::Capture: return { { Who, TEXT("Catch an Echo in the tall grass first. A Ranger with one Echo is just a person with a pet.") } };
		case EPBXStep::RhoBattle: return { { Who, TEXT("You caught one already? Okay, okay. Let's see if it can take a hit.") }, { Who, TEXT("Rival battle!") } };
		default: return { { Who, TEXT("Not bad, Ranger. Not bad at all. See you on Route 1 — I'll be the one complaining about the hills.") } };
		}
	}
	if (Who == TEXT("vale"))
	{
		if (S <= EPBXStep::Starter) return { { Who, TEXT("Welcome to Veyra's newest Ranger! Every Lattice card holds an Echo — the trace a Pokémon leaves in a storage relay.") },
			{ Who, TEXT("Lately the Echoes have started walking out of their cards. They hold the shape of the Pokémon printed on them.") },
			{ Who, TEXT("You will need a partner. Choose one of these three cards — its Echo will walk with you.") } };
		if (S == EPBXStep::Capture) return { { Who, TEXT("The tall grass by the west road, Ranger. Weaken a wild Echo, then throw a Poké Ball.") } };
		if (S == EPBXStep::RhoBattle) return { { Who, TEXT("Rho is waiting for you at the Route 1 gate. Go easy on him... or don't.") } };
		return { { Who, TEXT("Your licence is signed. Route 1 leads west to Mistvale — the fog there has been acting strange.") } };
	}
	if (Who == TEXT("aide")) return { { Who, TEXT("The relay hums louder every week. Dr. Vale says that's the Echoes waking up. I say it's the coffee machine.") } };
	if (Who == TEXT("fisher")) return { { Who, TEXT("Tide brings in odd things lately. Saw a wave shaped like a Lapras last week. Probably nothing.") } };
	if (Who == TEXT("gardener")) return { { Who, P ? TEXT("Keep your Echo out of my tulips, Ranger. They nibble.") : TEXT("Echoes love my flowerbeds. Little thieves!") } };
	if (Who == TEXT("merchant")) return { { Who, TEXT("Fresh apples! Well — for Echoes. Rangers pay double.") } };
	if (Who == TEXT("kid")) return { { Who, P ? FString::Printf(TEXT("Whoa! Is that YOUR %s?! When I grow up I'm gonna have a hundred Echoes!"), *PName) : TEXT("When I grow up I'm gonna be a Ranger and have a hundred Echoes!") } };
	if (Who == TEXT("guard"))
	{
		if (S >= EPBXStep::Gate) return { { Who, TEXT("Licence signed? Then don't wait for us to dig this out — the train to Mistvale leaves from Lumen Station, east end of town.") } };
		return { { Who, TEXT("Route 1's shut. Landslide came down on Tuesday and took half the road with it.") }, { Who, TEXT("Until it's cleared, the only way to Mistvale is the train. Licensed Rangers only, mind.") } };
	}
	if (Who == TEXT("conductor"))
	{
		if (S >= EPBXStep::Gate) return { { Who, TEXT("A signed licence! Dr. Vale's handwriting, no mistaking it.") }, { Who, TEXT("All aboard whenever you're ready — the middle carriage, platform side.") } };
		return { { Who, TEXT("Lumen Station, end of the line! Or the start of it, depends which way you're facing.") }, { Who, TEXT("Mistvale's two hours through the mountain. Rangers ride free with a signed licence.") } };
	}
	return { { Who, TEXT("...") } };
}

// =================================================================== story
EPBXStep APBXDirector::Step() const { return Game ? Game->Step() : EPBXStep::WakeUp; }

void APBXDirector::SetStep(EPBXStep S)
{
	if (!Game) return;
	Game->SetStep(S); PBXLOG("[PBX] step -> %d", (int32)S);
	RefreshWorld();
}

void APBXDirector::RefreshWorld()
{
	const EPBXStep S = Step();
	// Rho: outside your house at the start, at the Route 1 gate afterwards
	if (TObjectPtr<APBXNPC>* R = NPCs.Find(TEXT("rho")))
	{
		const FString Key = S <= EPBXStep::MeetRho ? TEXT("rho_greet") : TEXT("rho_gate");
		if (const FPBXSpot* Sp = Spots.Find(Key))
		{
			const float Z = PBXWorld::GroundZ(GetWorld(), Sp->Pos, 300.f, 1500.f, Sp->Pos.Z);
			if (FVector::Dist2D((*R)->GetActorLocation(), Sp->Pos) > 300.f) (*R)->SetActorLocationAndRotation(FVector(Sp->Pos.X, Sp->Pos.Y, Z + 92.f), FRotator(0, Sp->Yaw, 0), false, nullptr, ETeleportType::TeleportPhysics);
			(*R)->Home = (*R)->GetActorLocation(); (*R)->HomeYaw = Sp->Yaw;
		}
	}
	// "!" markers on whoever the story wants you to see
	for (auto& KV : NPCs)
	{
		bool M = false;
		if (KV.Key == TEXT("vale")) M = S == EPBXStep::GoLab || S == EPBXStep::Starter;
		if (KV.Key == TEXT("rho")) M = S == EPBXStep::RhoBattle;
		if (KV.Key == TEXT("mom")) M = S == EPBXStep::WakeUp;
		KV.Value->SetMarker(M);
	}
	// the gate
	for (AActor* A : GateBarrier) if (A) { A->SetActorHiddenInGame(false); A->SetActorEnableCollision(true); }   // Route 1: landslide
	// cards on the table
	for (int32 i = 0; i < TableCards.Num(); i++) if (TableCards[i])
	{
		bool bTaken = false; if (Game && Game->State) for (const FPBXMon& Mo : Game->State->Team) if (Mo.Card == PBXData::Starters()[i]) bTaken = true;
		TableCards[i]->SetActorHiddenInGame(bTaken || S < EPBXStep::GoLab);
	}
	if (S >= EPBXStep::Capture) SpawnPartner(false);
}

FVector APBXDirector::ObjectiveTarget(FString& Label) const
{
	auto DoorOf = [&](const TCHAR* Id, bool bOut) { for (const FPBXDoor& D : Doors) if (D.Id == Id) return bOut ? D.OutDoor : D.InDoor; return FVector::ZeroVector; };
	auto NpcLoc = [&](const TCHAR* Id) { const TObjectPtr<APBXNPC>* N = NPCs.Find(Id); return N ? (*N)->GetActorLocation() : FVector::ZeroVector; };
	const bool bIn = Inside(); const bool bInLab = bIn && FVector::Dist2D(PlayerLoc(), DoorOf(TEXT("lab"), false)) < 2500.f;
	switch (Step())
	{
	case EPBXStep::WakeUp: Label = TEXT("Head outside — Dr. Vale is expecting you"); return bIn ? DoorOf(TEXT("house"), false) : DoorOf(TEXT("lab"), true);
	case EPBXStep::MeetRho: Label = TEXT("Someone is waiting outside"); return NpcLoc(TEXT("rho"));
	case EPBXStep::GoLab: case EPBXStep::Starter: Label = TEXT("Meet Dr. Vale at Pokébox Labs"); return bInLab ? NpcLoc(TEXT("vale")) : bIn ? DoorOf(TEXT("house"), false) : DoorOf(TEXT("lab"), true);
	case EPBXStep::Capture: Label = TEXT("Catch a wild Echo in the tall grass by the west road"); return bIn ? (bInLab ? DoorOf(TEXT("lab"), false) : DoorOf(TEXT("house"), false)) : (Grass.Num() ? FVector(Grass[0].GetCenter(), 0) : FVector::ZeroVector);
	case EPBXStep::RhoBattle: Label = TEXT("Rho wants a battle — meet him at the Route 1 gate"); return bIn ? (bInLab ? DoorOf(TEXT("lab"), false) : DoorOf(TEXT("house"), false)) : NpcLoc(TEXT("rho"));
	case EPBXStep::Rest: Label = TEXT("Rest your team at home (your bed)"); return bIn ? (bInLab ? DoorOf(TEXT("lab"), false) : BedPos) : DoorOf(TEXT("house"), true);
	case EPBXStep::Gate: Label = TEXT("Catch the train to Mistvale at Lumen Station"); return bIn ? (bInLab ? DoorOf(TEXT("lab"), false) : DoorOf(TEXT("house"), false)) : (bHasTrain ? TrainBoard.Pos : GatePos);
	default: Label = TEXT("Chapter complete! Explore Lumen Harbor"); return FVector::ZeroVector;
	}
}

void APBXDirector::UpdateObjective()
{
	UI->Chapter = TEXT("Chapter 1 · A Licence to Remember");
	FString L; const FVector T = ObjectiveTarget(L); UI->Objective = L;
	if (T.IsZero() || !Player) { UI->bArrow = false; UI->Distance = -1; return; }
	const FVector P = PlayerLoc();
	UI->Distance = FMath::RoundToInt(FVector::Dist2D(P, T) / 100.f); UI->bArrow = UI->Distance > 2;
	float CamYaw = Player->GetControlRotation().Yaw;
	if (APlayerCameraManager* PCM = UGameplayStatics::GetPlayerCameraManager(this, 0)) CamYaw = PCM->GetCameraRotation().Yaw;
	UI->ArrowAngle = FRotator::NormalizeAxis((T - P).Rotation().Yaw - CamYaw) - 90.f;
}

void APBXDirector::StoryTick(float Dt)
{
	if (!Player || !Game) return;
	const FVector P = PlayerLoc(); const EPBXStep S = Step();
	// Rho's greeting the first time you step outside
	if (S == EPBXStep::MeetRho && !Inside())
	{
		if (TObjectPtr<APBXNPC>* R = NPCs.Find(TEXT("rho")))
		{
			APBXNPC* N = *R; N->FaceTowards(P); Player->FaceTowards(N->GetActorLocation());
			N->PlayAction(TEXT("Idle_Talking_Loop"), true);
			QSay({ { TEXT("rho"), TEXT("Hey, neighbour! Big day — you're Lumen Harbor's new Lattice Ranger! I'm Rho: relay courier, tour guide, part-time panic.") },
				   { TEXT("rho"), TEXT("Dr. Vale is waiting at Pokébox Labs. Big building, satellite dish, can't miss it. Follow the arrow!") },
				   { TEXT("rho"), TEXT("Me? I'm off to the Route 1 gate. Come find me once you've got a partner — I want a battle!") } });
			QDo([this, N] { N->ReturnToIdle(); SetStep(EPBXStep::GoLab); SaveNow(false); });
		}
		return;
	}
	// soft world limits: deep water, the forest edge, and the closed gate
	SafeT += Dt; WarnT -= Dt;
	if (!Inside())
	{
		auto Gate = [&](const FVector& Q) { return Q.X < GatePos.X - 150.f && FMath::Abs(Q.Y - GatePos.Y) < 2500.f; };
		auto Bad = [&](const FVector& Q) { return Q.Z < WaterZ || FVector2D::Distance(FVector2D(Q.X, Q.Y), BoundsCenter) > BoundsRadius || Gate(Q); };
		const bool bGateClosed = Gate(P);
		if (Bad(P))
		{
			// old saves (chapter end used to be past the gate) can leave LastSafe outside too: fall back to the town square
			if (Bad(LastSafe)) LastSafe = SafeSpot.Pos + FVector(0, 0, 100);
			TeleportPlayer(LastSafe, Player->GetActorRotation().Yaw);
			if (WarnT <= 0.f)
			{
				WarnT = 3.f;
				Toast(bGateClosed ? TEXT("Route 1 is buried under a landslide. The train is the way to Mistvale.") : P.Z < WaterZ ? TEXT("Too deep! Your Echo can't swim yet.") : TEXT("The forest is too thick here — stay near the town."));
			}
		}
		else if (SafeT > .5f && Player->GetCharacterMovement()->IsMovingOnGround()) { LastSafe = P; SafeT = 0.f; }
	}
	else if (SafeT > .5f && Player->GetCharacterMovement()->IsMovingOnGround()) { LastSafe = P; SafeT = 0.f; }
	// walking into a wild Echo starts a battle
	if (Game->HasPartner() && !Inside())
		for (APBXEcho* W : Wilds) if (W && !W->IsHidden() && FVector::Dist2D(W->GetActorLocation(), P) < 170.f) { StartWildBattle(W); break; }
}

void APBXDirector::UpdateWilds(float Dt)
{
	const bool bWant = Step() >= EPBXStep::Capture && Grass.Num() > 0;
	if (bWant && Wilds.Num() == 0)
	{
		const TArray<FName> Pool = PBXData::WildPool();
		for (int32 i = 0; i < WildSpawns.Num(); i++)
		{
			APBXEcho* E = GetWorld()->SpawnActor<APBXEcho>(APBXEcho::StaticClass(), FTransform(WildSpawns[i]));
			if (!E) continue;
			const FName Card = Pool[i % Pool.Num()]; const FPBXCardDef* C = PBXData::Card(Card);
			E->Setup(Card, 90.f * (C ? C->Size : 1.f)); E->bWild = true; E->PlaceAt(WildSpawns[i]); E->Mode = APBXEcho::EMode::Wander;
			for (const FBox2D& B : Grass) if (B.IsInside(FVector2D(WildSpawns[i].X, WildSpawns[i].Y))) E->WanderBox = B;
			if (!E->WanderBox.bIsValid && Grass.Num()) E->WanderBox = Grass[0];
			E->Tags.Add(TEXT("respawn0"));
			Wilds.Add(E);
		}
	}
	// beaten / caught Echoes come back after a while (a different one)
	for (APBXEcho* E : Wilds) if (E && E->IsHidden())
	{
		float* T = nullptr; static TMap<TWeakObjectPtr<APBXEcho>, float> Timers; T = &Timers.FindOrAdd(E);
		*T += Dt;
		if (*T > 25.f)
		{
			*T = 0.f; const TArray<FName> Pool = PBXData::WildPool(); const FName Card = Pool[FMath::RandRange(0, Pool.Num() - 1)];
			const FPBXCardDef* C = PBXData::Card(Card); E->Setup(Card, 90.f * (C ? C->Size : 1.f));
			const FVector2D Pt(FMath::FRandRange(E->WanderBox.Min.X, E->WanderBox.Max.X), FMath::FRandRange(E->WanderBox.Min.Y, E->WanderBox.Max.Y));
			E->PlaceAt(FVector(Pt, 0)); E->SetFaint(false); E->SetActorHiddenInGame(false); E->Mode = APBXEcho::EMode::Wander; E->PopIn();
		}
	}
}

void APBXDirector::BoardTrain()
{
	if (bTrainGo || !Train.Num()) { CompleteChapter(); return; }
	QSay({ { TEXT("conductor"), TEXT("All aboard for Mistvale! Mind the gap, Ranger.") } });
	QFade(1.f, .5f);
	QDo([this]
	{
		Player->SetActorHiddenInGame(true); if (Partner) Partner->SetActorHiddenInGame(true);
		if (APlayerController* PC = GetWorld()->GetFirstPlayerController())
		{
			Cam->SetActorLocationAndRotation(TrainCam.Pos, FRotator(-8.f, TrainCam.Yaw, 0)); Cam->GetCameraComponent()->SetFieldOfView(62.f); PC->SetViewTarget(Cam);
		}
		UI->Prompt.Empty(); bTrainGo = true; TrainV = 0.f;
	});
	QFade(0.f, .6f);
	QWait(1.2f);
	QDo([this] { Splash(TEXT("NEXT STOP: MISTVALE"), TEXT("Chapter 1 complete")); });
	QWait(5.5f);
	QFade(1.f, .8f);
	QDo([this]
	{
		Player->SetActorHiddenInGame(false); if (Partner) Partner->SetActorHiddenInGame(false);
		if (APlayerController* PC = GetWorld()->GetFirstPlayerController()) PC->SetViewTarget(Player);
		CompleteChapter();
	});
	QFade(0.f, .5f);
}

void APBXDirector::TickTrain(float Dt)
{
	if (!bTrainGo) return;
	TrainV = FMath::Min(TrainV + 260.f * Dt, 2200.f);          // pulls away gently, then speeds up into the tunnel
	for (AActor* A : Train) if (A)
	{
		A->AddActorWorldOffset(TrainDir * TrainV * Dt);
		if (A->GetActorLocation().Y > TrainExitY) A->SetActorHiddenInGame(true);
	}
	// the camera pans to follow the locomotive
	if (Cam && Train.Num() && Train[0] && !Train[0]->IsHidden())
	{
		const FRotator R = (Train[0]->GetActorLocation() + FVector(0, 0, 250) - Cam->GetActorLocation()).Rotation();
		Cam->SetActorRotation(FMath::RInterpTo(Cam->GetActorRotation(), R, Dt, 2.5f));
	}
}

void APBXDirector::CompleteChapter()
{
	SetStep(EPBXStep::Done); SaveNow(false);
	ShowMenu(EMenu::Complete);
}

// =================================================================== battles
static FPBXFighter FighterOf(const FPBXMon& M)
{
	const FPBXCardDef* C = PBXData::Card(M.Card); FPBXFighter F = FPBXFighter::Make(*C, M.Lv, PBXData::LvMult(M.Lv));
	if (M.HP >= 0) F.HP = FMath::Min(M.HP, F.MaxHP);
	return F;
}

void APBXDirector::SetupStage(const FVector& FoePos)
{
	const FVector P = PlayerLoc();
	FVector D = FoePos - P; D.Z = 0; if (D.SizeSquared() < 1.f) D = Player->GetActorForwardVector(); D.Normalize();
	const FVector Side(-D.Y, D.X, 0);
	Bt.D = D; Bt.Side = Side;
	Bt.A = P + D * 240.f - Side * 60.f; Bt.Bp = P + D * 860.f + Side * 40.f;
	Bt.A.Z = PBXWorld::GroundZ(GetWorld(), Bt.A, 300.f, 1500.f, P.Z - 90.f); Bt.Bp.Z = PBXWorld::GroundZ(GetWorld(), Bt.Bp, 300.f, 1500.f, P.Z - 90.f);
	Player->GetCharacterMovement()->StopMovementImmediately(); Player->FaceTowards(Bt.Bp, true);
	// camera: behind and beside your Echo, the foe big in the upper right; pick the side with fewer obstacles
	const float Dist = 740.f; float BestS = 1.f; int32 BestHits = 99;
	FCollisionQueryParams QP(SCENE_QUERY_STAT(PBXCam), false); QP.AddIgnoredActor(Player);
	for (auto& KV : NPCs) QP.AddIgnoredActor(KV.Value);
	for (float S : { 1.f, -1.f })
	{
		FVector C = Bt.A - D * Dist * .62f + Side * S * Dist * .4f; C.Z = FMath::Max(Bt.A.Z + 210.f + Dist * .16f, PBXWorld::GroundZ(GetWorld(), C, 500.f, 2000.f, Bt.A.Z) + 150.f);
		int32 Hits = 0;
		for (const FVector& T : { Bt.A, Bt.Bp, (Bt.A + Bt.Bp) * .5f }) if (GetWorld()->LineTraceTestByChannel(C, T + FVector(0, 0, 110), ECC_Visibility, QP)) Hits++;
		if (Hits < BestHits) { BestHits = Hits; BestS = S; }
	}
	Bt.CamS = BestS;
	FVector C = Bt.A - D * Dist * .62f + Side * BestS * Dist * .4f; C.Z = FMath::Max(Bt.A.Z + 210.f + Dist * .16f, PBXWorld::GroundZ(GetWorld(), C, 500.f, 2000.f, Bt.A.Z) + 150.f);
	const FVector Look = FMath::Lerp(Bt.A, Bt.Bp, .62f) + FVector(0, 0, 90);
	Cam->SetActorLocationAndRotation(C, (Look - C).Rotation());
	if (APlayerController* PC = GetWorld()->GetFirstPlayerController()) PC->SetViewTargetWithBlend(Cam, .6f, VTBlend_Cubic);
}

void APBXDirector::StartWildBattle(APBXEcho* W)
{
	if (Bt.bActive || !W || !Partner) return;
	TArray<FPBXFighter> Mine; for (const FPBXMon& M : Game->State->Team) Mine.Add(FighterOf(M));
	int32 First = Mine.IndexOfByPredicate([](const FPBXFighter& F) { return F.HP > 0; });
	if (First < 0) { TeleportPlayer(LastSafe, Player->GetActorRotation().Yaw); Toast(TEXT("Your team is exhausted — rest at home first.")); return; }
	Bt = FBattleCtx(); Bt.bActive = true; Bt.bWild = true; Bt.Foe = W; Bt.Mine = Partner;
	const FPBXCardDef* C = PBXData::Card(W->CardId); Bt.FoeLv = FMath::RandRange(10, 12);
	FPBXFighter Foe = FPBXFighter::Make(*C, Bt.FoeLv, PBXData::LvMult(Bt.FoeLv));
	Bt.bStory = Step() == EPBXStep::Capture; if (Bt.bStory) Foe.MinHP = 1;
	Bt.B.Team[0] = Mine; Bt.B.Team[1] = { Foe }; Bt.B.Act[0] = First;
	Game->State->Seen.AddUnique(W->CardId);
	SetupStage(W->GetActorLocation());
	W->Mode = APBXEcho::EMode::Stage; W->PlaceAt(Bt.Bp); W->Flash(FLinearColor(1, 1, 1), 3.f);
	Partner->Mode = APBXEcho::EMode::Stage; if (Mine[First].CardId != Partner->CardId) { const FPBXCardDef* PC2 = PBXData::Card(Mine[First].CardId); Partner->Setup(Mine[First].CardId, 95.f * PC2->Size); }
	Partner->PlaceAt(Bt.A); Partner->PopIn();
	UI->Mode = EPBXUIMode::Battle; UI->Log = FString(); UI->bMoves = false;
	UI->Banner = FString::Printf(TEXT("A wild %s appeared!"), *C->Name); UI->BannerT = 1.7f;
	SyncPlates(); UI->Plate[0].ShownHP = UI->Plate[0].HP; UI->Plate[1].ShownHP = UI->Plate[1].HP;
	PBXLOG("[PBX] wild battle vs %s Lv%d", *C->Name, Bt.FoeLv);
	QWait(1.7f); QDo([this] { ShowMoves(); });
}

void APBXDirector::StartTrainerBattle(FName Who)
{
	if (Bt.bActive || !Partner) return;
	TArray<FPBXFighter> Mine; for (const FPBXMon& M : Game->State->Team) Mine.Add(FighterOf(M));
	int32 First = Mine.IndexOfByPredicate([](const FPBXFighter& F) { return F.HP > 0; });
	if (First < 0) { QSay({ { Who, TEXT("Your Echoes look wiped out. Go rest first — I'll wait. Probably.") } }); return; }
	APBXNPC* N = NPCs.FindRef(Who); if (!N) return;
	Bt = FBattleCtx(); Bt.bActive = true; Bt.bTrainer = true; Bt.Trainer = Who; Bt.Mine = Partner;
	const FPBXCardDef* C = PBXData::Card(PBXData::RivalCard()); Bt.FoeLv = 8;
	FPBXFighter Foe = FPBXFighter::Make(*C, Bt.FoeLv, .8f);
	Bt.B.Team[0] = Mine; Bt.B.Team[1] = { Foe }; Bt.B.Act[0] = First;
	SetupStage(N->GetActorLocation());
	APBXEcho* E = GetWorld()->SpawnActor<APBXEcho>(APBXEcho::StaticClass(), FTransform(Bt.Bp));
	if (E) { E->Setup(C->Id, 95.f * C->Size); E->PlaceAt(Bt.Bp); E->Mode = APBXEcho::EMode::Stage; E->PopIn(); }
	Bt.Foe = E; Bt.bOwnsFoe = true;
	const FVector RhoAt = Bt.Bp + Bt.D * 230.f + Bt.Side * 120.f;
	N->SetActorLocation(FVector(RhoAt.X, RhoAt.Y, PBXWorld::GroundZ(GetWorld(), RhoAt, 300.f, 1500.f, RhoAt.Z) + 92.f), false, nullptr, ETeleportType::TeleportPhysics);
	N->FaceTowards(PlayerLoc(), true); N->PlayAction(TEXT("Spell_Simple_Idle_Loop"), true);
	Partner->Mode = APBXEcho::EMode::Stage; if (Mine[First].CardId != Partner->CardId) { const FPBXCardDef* PC2 = PBXData::Card(Mine[First].CardId); Partner->Setup(Mine[First].CardId, 95.f * PC2->Size); }
	Partner->PlaceAt(Bt.A); Partner->PopIn();
	Player->PlayAction(TEXT("Spell_Simple_Idle_Loop"), true);
	UI->Mode = EPBXUIMode::Battle; UI->Log = FString(); UI->bMoves = false;
	UI->Banner = FString::Printf(TEXT("%s wants to battle!"), *N->DisplayName); UI->BannerT = 1.8f;
	SyncPlates(); UI->Plate[0].ShownHP = UI->Plate[0].HP; UI->Plate[1].ShownHP = UI->Plate[1].HP;
	PBXLOG("[PBX] trainer battle vs %s", *Who.ToString());
	QWait(1.8f); QDo([this] { ShowMoves(); });
}

void APBXDirector::SyncPlates()
{
	for (int32 s = 0; s < 2; s++)
	{
		const FPBXFighter& F = Bt.B.Active(s); FPBXPlate& P = UI->Plate[s];
		P.bShow = true; P.Name = F.Name; P.Type = F.Type; P.Lv = F.Lv; P.HP = F.HP; P.MaxHP = F.MaxHP; P.Energy = F.Energy; P.Status = F.Status.IsNone() ? FString() : F.Status.ToString();
	}
}

void APBXDirector::ShowMoves()
{
	if (!Bt.bActive) return;
	const FPBXFighter& Me = Bt.B.Active(0); const FPBXFighter& Foe = Bt.B.Active(1);
	const FPBXSig& Sig = FPBXBattle::SigOf(Me.Type);
	UI->Moves.Reset(); Bt.MoveCodes.Reset();
	auto Add = [&](int32 Code, const FString& T, const FString& S, bool bOk, FLinearColor Col)
	{
		FPBXOption O; O.Title = T; O.Sub = S; O.bEnabled = bOk; O.Color = Col; O.Key = FString::FromInt(UI->Moves.Num() + 1); UI->Moves.Add(O); Bt.MoveCodes.Add(Code);
	};
	const FLinearColor TC = PBXData::TypeColor(Me.Type);
	Add(0, TEXT("Attack"), FString::Printf(TEXT("~%d dmg · +1 energy"), Bt.B.Estimate(Me, Foe, EPBXMove::Attack)), true, FLinearColor(.8f, .8f, .8f));
	Add(1, Sig.Name, FString::Printf(TEXT("~%d dmg · 2 energy · %s"), Bt.B.Estimate(Me, Foe, EPBXMove::Sig), *Sig.Note), Bt.B.CanUse(Me, EPBXMove::Sig), TC);
	Add(2, TEXT("Ultimate"), FString::Printf(TEXT("~%d dmg · 4 energy"), Bt.B.Estimate(Me, Foe, EPBXMove::Ult)), Bt.B.CanUse(Me, EPBXMove::Ult), FLinearColor(1, .7f, .2f));
	Add(3, TEXT("Guard"), TEXT("halves damage · +1 energy"), true, FLinearColor(.4f, .7f, 1));
	int32 Alive = 0; for (int32 i = 0; i < Bt.B.Team[0].Num(); i++) if (i != Bt.B.Act[0] && Bt.B.Team[0][i].HP > 0) Alive++;
	if (Alive) Add(4, TEXT("Switch"), TEXT("send in your next Echo"), true, FLinearColor(.6f, .9f, .6f));
	if (Bt.bWild)
	{
		Add(5, TEXT("Poké Ball"), FString::Printf(TEXT("%d%% chance · weaken it first"), FMath::RoundToInt(Bt.B.CaptureChance() * 100)), true, FLinearColor(.95f, .3f, .3f));
		Add(6, TEXT("Run"), TEXT("escape"), !Bt.bStory || true, FLinearColor(.7f, .7f, .7f));
	}
	UI->MoveSel = 0; UI->MovesRev++; UI->bMoves = true; SyncPlates();
	UI->OnMove = [this](int32 i) { PickMove(i); };
	UI->Log = FString::Printf(TEXT("What will %s do?"), *Me.Name);
	if (bAuto)
	{
		const float HpK = float(Foe.HP) / FMath::Max(1, Foe.MaxHP);
		int32 Code = 0;
		if (Bt.bWild && (HpK < .45f || Foe.HP <= 1)) Code = 5;
		else if (Bt.B.CanUse(Me, EPBXMove::Ult)) Code = 2;
		else if (Bt.B.CanUse(Me, EPBXMove::Sig)) Code = 1;
		const int32 Idx = Bt.MoveCodes.IndexOfByKey(Code);
		QWait(.7f); QDo([this, Idx] { if (UI->bMoves) PickMove(Idx); });
	}
}

void APBXDirector::Floater(const FVector& W, const FString& T, const FLinearColor& C)
{
	int32 Best = 0; for (int32 i = 0; i < 8; i++) if (UI->Floaters[i].T > UI->Floaters[Best].T) Best = i;
	FPBXFloater& F = UI->Floaters[Best]; F.World = W; F.Text = T; F.Color = C; F.T = 0.f; F.Scale = 1.8f;
}

void APBXDirector::PickMove(int32 i)
{
	if (!Bt.bActive || !UI->bMoves || !Bt.MoveCodes.IsValidIndex(i) || !UI->Moves[i].bEnabled) return;
	const int32 Code = Bt.MoveCodes[i];
	UI->bMoves = false;
	if (Code == 5) { TryCapture(); return; }
	if (Code == 6) { UI->Log = TEXT("Got away safely!"); QWait(1.f); QDo([this] { EndBattle(TEXT("run")); }); return; }
	EPBXMove M = Code == 0 ? EPBXMove::Attack : Code == 1 ? EPBXMove::Sig : Code == 2 ? EPBXMove::Ult : Code == 3 ? EPBXMove::Guard : EPBXMove::Switch;
	int32 To = -1;
	if (M == EPBXMove::Switch) for (int32 k = 1; k <= Bt.B.Team[0].Num(); k++) { const int32 j = (Bt.B.Act[0] + k) % Bt.B.Team[0].Num(); if (Bt.B.Team[0][j].HP > 0 && j != Bt.B.Act[0]) { To = j; break; } }
	PlayEvents(DoRound(M, To));
}

TArray<FPBXEvent> APBXDirector::DoRound(EPBXMove M, int32 To)
{
	for (int32 s = 0; s < 2; s++) { Bt.PreHP[s].Reset(); for (const FPBXFighter& F : Bt.B.Team[s]) Bt.PreHP[s].Add(F.HP); Bt.PreAct[s] = Bt.B.Act[s]; }
	return Bt.B.Round(M, To);
}

void APBXDirector::PlayEvents(const TArray<FPBXEvent>& Ev)
{
	// replay the round step by step; Plate HP follows a running copy so the bars drop hit by hit
	struct FSim { TArray<int32> HP[2]; int32 Act[2]; };
	TSharedPtr<FSim> Sim = MakeShared<FSim>();
	for (int32 s = 0; s < 2; s++) { Sim->HP[s] = Bt.PreHP[s]; Sim->Act[s] = Bt.PreAct[s]; }
	auto EchoOf = [this](int32 Side) -> APBXEcho* { return Side == 0 ? Bt.Mine.Get() : Bt.Foe.Get(); };
	auto Who = [this](int32 Side, const FString& N) { return Side == 0 ? N : (Bt.bWild ? FString::Printf(TEXT("The wild %s"), *N) : FString::Printf(TEXT("%s's %s"), *SpeakerName(Bt.Trainer), *N)); };
	auto ShowHP = [this, Sim](int32 Side) { const FPBXFighter& F = Bt.B.Team[Side][Sim->Act[Side]]; FPBXPlate& P = UI->Plate[Side]; P.Name = F.Name; P.Type = F.Type; P.Lv = F.Lv; P.MaxHP = F.MaxHP; P.HP = FMath::Max(0, Sim->HP[Side][Sim->Act[Side]]); };
	for (const FPBXEvent& E0 : Ev)
	{
		const FPBXEvent E = E0;
		switch (E.Kind)
		{
		case FPBXEvent::Hit:
		{
			QDo([this, E, EchoOf, Who, Sim]
			{
				const FPBXFighter& A = Bt.B.Team[E.Side][Sim->Act[E.Side]];
				UI->Log = FString::Printf(TEXT("%s used %s!"), *Who(E.Side, A.Name), *E.Move);
				if (APBXEcho* M = EchoOf(E.Side)) M->Lunge(E.Side == 0 ? Bt.D : -Bt.D, E.MoveKind == EPBXMove::Ult ? 260.f : 160.f);
				if (E.Side == 0 && Player) Player->PlayAction(E.MoveKind == EPBXMove::Attack ? TEXT("Punch_Jab") : TEXT("Spell_Simple_Shoot"), false, .1f);
			});
			QWait(.24f);
			QDo([this, E, EchoOf, ShowHP, Sim]
			{
				const int32 T = 1 - E.Side; int32& H = Sim->HP[T][Sim->Act[T]]; H = FMath::Max(Bt.B.Team[T][Sim->Act[T]].MinHP, H - E.Dmg); ShowHP(T);
				if (APBXEcho* V = EchoOf(T)) { V->Hurt(); V->Flash(PBXData::TypeColor(E.Type), 4.f); Floater(V->GetActorLocation(), FString::Printf(TEXT("-%d"), E.Dmg), E.bCrit ? FLinearColor(1, .85f, .1f) : FLinearColor::White); }
				FString Extra = E.bEff ? TEXT("  It's super effective!") : E.bWeak ? TEXT("  It's not very effective...") : FString();
				if (E.bCrit) Extra += TEXT("  A critical hit!"); if (E.bGuarded) Extra += TEXT("  (guarded)");
				if (!Extra.IsEmpty()) UI->Log += Extra;
				UI->ShakeT = (E.bCrit || E.MoveKind == EPBXMove::Ult) ? .45f : E.bEff ? .3f : .15f;
			});
			QWait(.85f);
			break;
		}
		case FPBXEvent::Guard: QDo([this, E, Who, Sim] { UI->Log = FString::Printf(TEXT("%s braces itself!"), *Who(E.Side, Bt.B.Team[E.Side][Sim->Act[E.Side]].Name)); }); QWait(.7f); break;
		case FPBXEvent::Para: QDo([this, E, Who, Sim] { UI->Log = FString::Printf(TEXT("%s is paralysed and can't move!"), *Who(E.Side, Bt.B.Team[E.Side][Sim->Act[E.Side]].Name)); }); QWait(.9f); break;
		case FPBXEvent::Status: QDo([this, E, Who, Sim] { UI->Log = FString::Printf(TEXT("%s was %s!"), *Who(E.Side, Bt.B.Team[E.Side][Sim->Act[E.Side]].Name), E.St == TEXT("burn") ? TEXT("burned") : TEXT("paralysed")); }); QWait(.8f); break;
		case FPBXEvent::Debuff: QDo([this, E, Who, Sim] { UI->Log = FString::Printf(TEXT("%s's %s fell!"), *Who(E.Side, Bt.B.Team[E.Side][Sim->Act[E.Side]].Name), *E.Stat); }); QWait(.7f); break;
		case FPBXEvent::Buff: QDo([this, E, Who, Sim] { UI->Log = FString::Printf(TEXT("%s's %s rose!"), *Who(E.Side, Bt.B.Team[E.Side][Sim->Act[E.Side]].Name), *E.Stat); }); QWait(.7f); break;
		case FPBXEvent::Heal: QDo([this, E, EchoOf, ShowHP, Sim] { Sim->HP[E.Side][Sim->Act[E.Side]] += E.Dmg; ShowHP(E.Side); if (APBXEcho* V = EchoOf(E.Side)) Floater(V->GetActorLocation(), FString::Printf(TEXT("+%d"), E.Dmg), FLinearColor(.4f, 1, .5f)); }); QWait(.5f); break;
		case FPBXEvent::Burn: QDo([this, E, EchoOf, ShowHP, Who, Sim] { Sim->HP[E.Side][Sim->Act[E.Side]] -= E.Dmg; ShowHP(E.Side); UI->Log = FString::Printf(TEXT("%s is hurt by its burn!"), *Who(E.Side, Bt.B.Team[E.Side][Sim->Act[E.Side]].Name)); if (APBXEcho* V = EchoOf(E.Side)) { V->Hurt(); Floater(V->GetActorLocation(), FString::Printf(TEXT("-%d"), E.Dmg), FLinearColor(1, .5f, .2f)); } }); QWait(.8f); break;
		case FPBXEvent::Cure: QDo([this, E, Who, Sim] { UI->Log = FString::Printf(TEXT("%s recovered from its %s."), *Who(E.Side, Bt.B.Team[E.Side][Sim->Act[E.Side]].Name), *E.St.ToString()); }); QWait(.6f); break;
		case FPBXEvent::KO: QDo([this, E, EchoOf, Who, Sim] { UI->Log = FString::Printf(TEXT("%s fainted!"), *Who(E.Side, Bt.B.Team[E.Side][Sim->Act[E.Side]].Name)); if (APBXEcho* V = EchoOf(E.Side)) V->SetFaint(true); }); QWait(1.1f); break;
		case FPBXEvent::Switch:
			QDo([this, E, EchoOf, ShowHP, Who, Sim]
			{
				Sim->Act[E.Side] = E.To; const FPBXFighter& F = Bt.B.Team[E.Side][E.To]; ShowHP(E.Side);
				if (APBXEcho* V = EchoOf(E.Side)) { const FPBXCardDef* C = PBXData::Card(F.CardId); V->Setup(F.CardId, 95.f * (C ? C->Size : 1.f)); V->SetFaint(false); V->PopIn(); V->Flash(FLinearColor::White, 4.f); }
				UI->Log = E.Side == 0 ? FString::Printf(TEXT("Go, %s!"), *F.Name) : FString::Printf(TEXT("%s sent out %s!"), *SpeakerName(Bt.Trainer), *F.Name);
			});
			QWait(1.f); break;
		default: break;
		}
	}
	QDo([this]
	{
		SyncPlates();
		if (Bt.B.Over.IsEmpty()) ShowMoves(); else EndBattle(Bt.B.Over);
	});
}

void APBXDirector::TryCapture()
{
	APBXEcho* F = Bt.Foe.Get(); if (!F) return;
	const float Chance = Bt.B.CaptureChance();
	const bool bCaught = FMath::FRand() < Chance;
	const int32 Shakes = bCaught ? 3 : FMath::RandRange(0, 2);
	UI->Log = FString::Printf(TEXT("You threw a Poké Ball! (%d%%)"), FMath::RoundToInt(Chance * 100));
	Player->PlayAction(TEXT("OverhandThrow"), false, .1f);
	AStaticMeshActor* Ball = GetWorld()->SpawnActor<AStaticMeshActor>(PlayerLoc() + FVector(0, 0, 60), FRotator::ZeroRotator);
	if (Ball)
	{
		Ball->SetMobility(EComponentMobility::Movable);
		Ball->GetStaticMeshComponent()->SetStaticMesh(LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Sphere.Sphere")));
		Ball->GetStaticMeshComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision); Ball->SetActorScale3D(FVector(.22f));
		if (UMaterialInterface* M = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/PBX/Materials/M_PBX_Color.M_PBX_Color")))
		{
			UMaterialInstanceDynamic* D = UMaterialInstanceDynamic::Create(M, Ball); D->SetVectorParameterValue(TEXT("Color"), FLinearColor(.85f, .08f, .06f)); D->SetScalarParameterValue(TEXT("Roughness"), .35f);
			Ball->GetStaticMeshComponent()->SetMaterial(0, D);
		}
	}
	Bt.Ball = Ball;
	const FVector From = PlayerLoc() + FVector(0, 0, 70), To = F->GetActorLocation() + FVector(0, 0, 60);
	QWait(.25f);
	Q([this, From, To](float T)
	{
		const float k = FMath::Clamp(T / .55f, 0.f, 1.f);
		if (AStaticMeshActor* B = Bt.Ball.Get()) B->SetActorLocation(FMath::Lerp(From, To, k) + FVector(0, 0, FMath::Sin(k * PI) * 220.f));
		return k >= 1.f;
	});
	QDo([this, F, To] { F->Flash(FLinearColor(1, .3f, .3f), 6.f); F->SetActorHiddenInGame(true); if (AStaticMeshActor* B = Bt.Ball.Get()) B->SetActorLocation(FVector(To.X, To.Y, PBXWorld::GroundZ(GetWorld(), To, 200.f, 800.f, To.Z) + 22.f)); });
	for (int32 i = 0; i < Shakes; i++)
	{
		QWait(.55f);
		QDo([this, i] { UI->Log = FString::ChrN(i + 1, TEXT('.')) + FString::Printf(TEXT(" %d"), i + 1); if (AStaticMeshActor* B = Bt.Ball.Get()) B->SetActorRotation(FRotator(0, 0, (i % 2 ? -1 : 1) * 25.f)); });
		QWait(.25f);
		QDo([this] { if (AStaticMeshActor* B = Bt.Ball.Get()) B->SetActorRotation(FRotator::ZeroRotator); });
	}
	QWait(.5f);
	if (bCaught)
	{
		QDo([this, F]
		{
			const FPBXFighter& Foe = Bt.B.Active(1);
			UI->Log = FString::Printf(TEXT("Gotcha! %s was captured!"), *Foe.Name);
			Splash(TEXT("GOTCHA!"), FString::Printf(TEXT("%s was bound to a blank Lattice card"), *Foe.Name), 2.4f);
		});
		QWait(2.f);
		QDo([this] { EndBattle(TEXT("caught")); });
	}
	else
	{
		QDo([this, F] { F->SetActorHiddenInGame(false); F->PopIn(); F->Flash(FLinearColor::White, 3.f); if (AStaticMeshActor* B = Bt.Ball.Get()) B->Destroy(); UI->Log = TEXT("Oh no! It broke free!"); });
		QWait(1.f);
		QDo([this] { PlayEvents(DoRound(EPBXMove::Switch, -1)); });   // the wild Echo gets a free turn
	}
}

void APBXDirector::SaveTeamHP()
{
	for (int32 i = 0; i < Game->State->Team.Num() && i < Bt.B.Team[0].Num(); i++)
	{
		FPBXMon& M = Game->State->Team[i]; const FPBXFighter& F = Bt.B.Team[0][i];
		M.HP = F.HP >= F.MaxHP ? -1 : FMath::Max(0, F.HP);
	}
}

void APBXDirector::EndBattle(const FString& Result)
{
	PBXLOG("[PBX] battle end: %s", *Result);
	SaveTeamHP();
	UI->bMoves = false;
	const bool bWin = Result == TEXT("win"), bLose = Result == TEXT("lose"), bCaught = Result == TEXT("caught");
	const FPBXFighter Foe = Bt.B.Active(1);
	if (bWin || bCaught)
	{
		const int32 Xp = 10 + Bt.FoeLv * 2;
		for (int32 i = 0; i < Game->State->Team.Num(); i++)
		{
			FPBXMon& M = Game->State->Team[i]; if (i < Bt.B.Team[0].Num() && Bt.B.Team[0][i].HP <= 0) continue;
			M.XP += Xp; bool bUp = false;
			while (M.XP >= M.Lv * 12 && M.Lv < 60) { M.XP -= M.Lv * 12; M.Lv++; bUp = true; }
			if (bUp) Toast(FString::Printf(TEXT("%s grew to Lv %d!"), *PBXData::Card(M.Card)->Name, M.Lv));
		}
	}
	if (bCaught)
	{
		const bool bTeam = Game->AddMon(Foe.CardId, Bt.FoeLv); Game->State->Captures++;
		Toast(FString::Printf(TEXT("%s joined %s."), *Foe.Name, bTeam ? TEXT("your team") : TEXT("your card box")));
	}
	if (bWin && Bt.bTrainer) { Game->State->Coins += 300; Game->State->Wins++; Toast(TEXT("You won 300 coins!")); }
	// tear down the stage
	if (AStaticMeshActor* B = Bt.Ball.Get()) B->Destroy();
	APBXEcho* F = Bt.Foe.Get();
	if (F) { if (Bt.bOwnsFoe) F->Destroy(); else { F->SetActorHiddenInGame(true); F->SetFaint(false); F->Mode = APBXEcho::EMode::Wander; } }
	if (APlayerController* PC = GetWorld()->GetFirstPlayerController()) PC->SetViewTargetWithBlend(Player, .6f, VTBlend_Cubic);
	Player->StopAction(.3f);
	const FName Trainer = Bt.Trainer; const bool bWasTrainer = Bt.bTrainer, bStory = Bt.bStory;
	for (int32 s = 0; s < 2; s++) UI->Plate[s].bShow = false;
	UI->Log = FString(); UI->Mode = EPBXUIMode::Explore;
	Bt.bActive = false;
	if (Partner) { Partner->Destroy(); Partner = nullptr; }
	SpawnPartner(false);
	if (APBXNPC* N = NPCs.FindRef(Trainer)) { N->SetActorLocation(N->Home, false, nullptr, ETeleportType::TeleportPhysics); N->ReturnToIdle(); }
	// story
	if (bCaught && Step() == EPBXStep::Capture)
	{
		QSay({ { TEXT("note"), TEXT("Your Lattice card buzzes. A message from Dr. Vale: \"Your first capture! Splendid. Rho is waiting for you at the Route 1 gate.\"") } });
		QDo([this] { SetStep(EPBXStep::RhoBattle); SaveNow(false); });
	}
	if (bWasTrainer && Trainer == TEXT("rho"))
	{
		APBXNPC* N = NPCs.FindRef(Trainer); if (N) { N->FaceTowards(PlayerLoc()); Player->FaceTowards(N->GetActorLocation()); }
		if (bWin)
		{
			QSay({ { TEXT("rho"), TEXT("Ow. Okay. You're good. Annoyingly good.") },
				   { TEXT("rho"), TEXT("Rule one of being a Ranger: rest your team. Go home, sleep in a real bed — it fixes everything. Trust me, I know.") } });
			QDo([this] { if (Step() == EPBXStep::RhoBattle) { SetStep(EPBXStep::Rest); SaveNow(false); } });
		}
		else QSay({ { TEXT("rho"), TEXT("Ha! Told you! ...Okay, go rest up and come back. I'm not going anywhere.") } });
	}
	if (bLose)
	{
		QDo([this] { UI->Mode = EPBXUIMode::Explore; });
		QSay({ { TEXT("note"), TEXT("Your team is out of energy! You hurry home...") } });
		QFade(1.f, .5f);
		QDo([this]
		{
			Game->HealAll();
			for (const FPBXDoor& D : Doors) if (D.Id == TEXT("house")) { FPBXSpot S = D.Inside; PlacePlayer(S); }
			if (Partner) Partner->PlaceAt(PlayerLoc());
		});
		QFade(0.f, .5f);
		QSay({ { TEXT("mom"), TEXT("Oh, sweetheart, look at you. Sit down — I'll make tea. Your Echoes are already feeling better.") } });
	}
	(void)bStory;
}

// =================================================================== menus
void APBXDirector::OpenChoice(const FString& Title, const FString& Sub, const TArray<FPBXOption>& Opts, bool bCards, TFunction<void(int32)> Pick)
{
	UI->ChoiceTitle = Title; UI->ChoiceSub = Sub; UI->Options = Opts; UI->bCards = bCards; UI->OnPick = MoveTemp(Pick);
	UI->Selected = 0; while (UI->Options.IsValidIndex(UI->Selected) && !UI->Options[UI->Selected].bEnabled) UI->Selected++;
	UI->OptionsRev++; UI->Mode = Menu != EMenu::None ? EPBXUIMode::Menu : EPBXUIMode::Choice;
}

void APBXDirector::CloseChoice() { UI->Options.Reset(); UI->OnPick = nullptr; UI->OptionsRev++; UI->Mode = EPBXUIMode::Explore; }

void APBXDirector::ShowMenu(EMenu M)
{
	Menu = M;
	auto Opt = [](const FString& T, const FString& S, bool bOk = true) { FPBXOption O; O.Title = T; O.Sub = S; O.bEnabled = bOk; O.Color = FLinearColor(.4f, .35f, .3f); return O; };
	switch (M)
	{
	case EMenu::Title:
	{
		if (Player) { Player->SetActorHiddenInGame(true); }
		if (APlayerController* PC = GetWorld()->GetFirstPlayerController()) { Cam->SetActorLocationAndRotation(FVector(4300, -3600, 1900), FRotator(-22, 138, 0)); PC->SetViewTarget(Cam); }
		UI->Fade = 0.f;
		const bool bSave = Game->HasSave();
		OpenChoice(TEXT("POKEBOX NEXT"), TEXT("Chapter 1 · A Licence to Remember"), { Opt(TEXT("Continue"), bSave ? TEXT("Load your saved game") : TEXT("No saved game yet"), bSave), Opt(TEXT("New Game"), TEXT("Start your journey as a Lattice Ranger")), Opt(TEXT("Quit"), TEXT("Back to the desktop")) }, false,
			[this](int32 i) { if (i == 0) ContinueGame(); else if (i == 1) ShowMenu(EMenu::Gender); else FPlatformMisc::RequestExit(false); });
		if (Game->HasSave()) UI->Selected = 0; else UI->Selected = 1;
		break;
	}
	case EMenu::Gender:
		OpenChoice(TEXT("WHO ARE YOU?"), TEXT("Pick how your Ranger looks"), { Opt(TEXT("Ranger · he / him"), TEXT("hoodie, sneakers, big grin")), Opt(TEXT("Ranger · she / her"), TEXT("bucket hat, red skirt, backpack")), Opt(TEXT("Back"), TEXT("")) }, false,
			[this](int32 i) { if (i == 2) ShowMenu(EMenu::Title); else StartNewGame(i == 0); });
		break;
	case EMenu::Pause:
		OpenChoice(TEXT("PAUSED"), FString::Printf(TEXT("Play time %d min · %d Echoes caught · %d coins"), FMath::FloorToInt(Game->State->PlayTime / 60.f), Game->State->Captures, Game->State->Coins),
			{ Opt(TEXT("Resume"), TEXT("")), Opt(TEXT("Save game"), TEXT("")), Opt(TEXT("Load last save"), TEXT(""), Game->HasSave()), Opt(TEXT("Controls"), TEXT("")), Opt(TEXT("Quit to title"), TEXT("")), Opt(TEXT("Quit game"), TEXT("")) }, false,
			[this](int32 i)
			{
				if (i == 0) { CloseChoice(); Menu = EMenu::None; }
				else if (i == 1) { CloseChoice(); Menu = EMenu::None; SaveNow(true); }
				else if (i == 2) { CloseChoice(); Menu = EMenu::None; ContinueGame(); }
				else if (i == 3) ShowMenu(EMenu::Controls);
				else if (i == 4) ToTitle();
				else FPlatformMisc::RequestExit(false);
			});
		break;
	case EMenu::Controls:
		OpenChoice(TEXT("CONTROLS"), TEXT("WASD / left stick: move · Mouse / right stick: camera · Shift / LT: run · Space: jump\nE / Enter / A: talk, interact, confirm · 1-7: battle moves · Mouse wheel / LB-RB: zoom · Esc / Start: pause"),
			{ Opt(TEXT("Back"), TEXT("")) }, false, [this](int32) { ShowMenu(EMenu::Pause); });
		break;
	case EMenu::Complete:
	{
		FString P = Game->HasPartner() ? PBXData::Card(Game->State->Team[0].Card)->Name : FString(TEXT("-"));
		OpenChoice(TEXT("CHAPTER 1 COMPLETE"), FString::Printf(TEXT("Route 1 to Mistvale is the next level.\nPartner: %s Lv %d · Echoes caught: %d · Play time: %d min"), *P, Game->HasPartner() ? Game->State->Team[0].Lv : 0, Game->State->Captures, FMath::FloorToInt(Game->State->PlayTime / 60.f)),
			{ Opt(TEXT("Keep exploring Lumen Harbor"), TEXT("your progress is saved")), Opt(TEXT("Quit to title"), TEXT("")) }, false,
			[this](int32 i)
			{
				if (i == 0) { CloseChoice(); Menu = EMenu::None; TeleportPlayer(GatePos + FVector(500, 0, 0), 0.f); }
				else ToTitle();
			});
		break;
	}
	default: break;
	}
	if (M == EMenu::Title || M == EMenu::Gender) UI->Mode = EPBXUIMode::Menu;
	if (M != EMenu::None) UI->Mode = EPBXUIMode::Menu;
}

void APBXDirector::StartNewGame(bool bMale)
{
	CloseChoice(); Menu = EMenu::None;
	Game->NewGame(bMale);
	if (Partner) { Partner->Destroy(); Partner = nullptr; }
	for (APBXEcho* W : Wilds) if (W) W->Destroy(); Wilds.Reset();
	Queue.Reset(); QueueGen++; StepT = 0.f;
	UI->Fade = 1.f;
	Player->ApplyLook(bMale ? TEXT("boy") : TEXT("f"), TEXT("Hair_Long"), .9f, bMale ? TEXT("player_m") : TEXT("player_f"), FLinearColor(.12f, .07f, .04f, 1));
	Player->SetActorHiddenInGame(false);
	PlacePlayer(NewGameSpot);
	if (APlayerController* PC = GetWorld()->GetFirstPlayerController()) PC->SetViewTarget(Player);
	RefreshWorld();
	QWait(.4f);
	QDo([this] { Player->PlayAction(TEXT("LayToIdle"), false, .05f); });
	QFade(0.f, 1.2f);
	QDo([this] { Splash(TEXT("CHAPTER 1"), TEXT("A Licence to Remember"), 3.f); });
	QWait(1.5f);
	PBXLOG("[PBX] new game (%s)", bMale ? TEXT("m") : TEXT("f"));
}

void APBXDirector::ContinueGame()
{
	if (!Game->Load()) { Toast(TEXT("No saved game.")); ShowMenu(EMenu::Title); return; }
	CloseChoice(); Menu = EMenu::None; Queue.Reset(); QueueGen++; StepT = 0.f;
	if (Partner) { Partner->Destroy(); Partner = nullptr; }
	Player->ApplyLook(Game->State->bMale ? TEXT("boy") : TEXT("f"), TEXT("Hair_Long"), .9f, Game->State->bMale ? TEXT("player_m") : TEXT("player_f"), FLinearColor(.12f, .07f, .04f, 1));
	Player->SetActorHiddenInGame(false);
	if (APlayerController* PC = GetWorld()->GetFirstPlayerController()) PC->SetViewTarget(Player);
	FPBXSpot S = NewGameSpot; if (Game->State->bHasPos) { S.Pos = Game->State->Pos - FVector(0, 0, 95.f); S.Yaw = Game->State->Yaw; }
	PlacePlayer(S);
	RefreshWorld(); SpawnPartner(false);
	UI->Fade = 1.f; QFade(0.f, .8f);
	QDo([this] { Toast(FString::Printf(TEXT("Welcome back, Ranger. (saved %s)"), *Game->State->SavedAt)); });
	PBXLOG("[PBX] continue: step %d", (int32)Step());
}

void APBXDirector::SaveNow(bool bToast)
{
	if (!Game || !Player) return;
	const bool bOk = Game->Save(Player->GetActorLocation(), Player->GetActorRotation().Yaw);
	if (bToast) Toast(bOk ? TEXT("Game saved.") : TEXT("Could not save!"));
	PBXLOG("[PBX] save %s (step %d)", bOk ? TEXT("ok") : TEXT("FAILED"), (int32)Step());
}

void APBXDirector::ToTitle()
{
	CloseChoice(); Queue.Reset(); QueueGen++; StepT = 0.f;
	if (Bt.bActive) { Bt.bActive = false; }
	ShowMenu(EMenu::Title);
}

// =================================================================== autoplay test
void APBXDirector::Shot(const FString& N)
{
	const FString Path = FPaths::ProjectSavedDir() / TEXT("pbx_auto") / (N + TEXT(".png"));
	FScreenshotRequest::RequestScreenshot(Path, true, false);
	AutoShots++; PBXLOG("[PBXAUTO] shot %s", *N);
}

void APBXDirector::AutoTick(float Dt)
{
	AutoT += Dt; AutoStepT += Dt;
	auto Fail = [this](const TCHAR* Why) { PBXLOG("[PBXAUTO] FAIL step %d: %s", AutoStep, Why); bAutoFail = true; AutoNext(); };
	auto Idle = [this] { return !Busy() && Menu == EMenu::None && !Bt.bActive && UI->Mode == EPBXUIMode::Explore; };
	auto DoorById = [this](const TCHAR* Id) -> const FPBXDoor* { for (const FPBXDoor& D : Doors) if (D.Id == Id) return &D; return nullptr; };
	if (AutoStepT > 90.f) { Fail(TEXT("timeout")); return; }
	switch (AutoStep)
	{
	case 0: if (AutoT > 4.f) { Shot(TEXT("01_title")); AutoNext(); } break;
	case 1: if (AutoStepT > 1.f) { ShowMenu(EMenu::Gender); AutoNext(); } break;
	case 2: if (AutoStepT > 1.f) { Shot(TEXT("02_gender")); StartNewGame(true); AutoNext(); } break;
	case 3: if (AutoStepT > 4.5f && Idle()) { Shot(TEXT("03_house")); if (APBXNPC* N = NPCs.FindRef(TEXT("mom"))) { TeleportPlayer(N->GetActorLocation() + N->GetActorForwardVector() * 150.f, 0); TalkTo(N); } AutoNext(); } break;
	case 4: if (AutoStepT > 1.2f && UI->Mode == EPBXUIMode::Dialogue && UI->Visible >= UI->Line.Len()) { Shot(TEXT("04_dialogue_mum")); AutoNext(); } break;
	case 5: if (Idle()) { if (const FPBXDoor* D = DoorById(TEXT("house"))) UseDoor(*D, false); AutoNext(); } break;
	case 6: if (UI->Mode == EPBXUIMode::Dialogue && UI->Visible >= UI->Line.Len() && AutoStepT > 1.5f) { Shot(TEXT("05_rho_greets")); AutoNext(); } break;
	case 7: if (Idle() && Step() == EPBXStep::GoLab) { Shot(TEXT("06_town_objective")); if (const FPBXDoor* D = DoorById(TEXT("lab"))) { FPBXSpot S = D->Outside; S.Pos += FRotator(0, S.Yaw, 0).Vector() * 600.f; S.Yaw += 180.f; PlacePlayer(S); } AutoNext(); } break;
	case 8: if (AutoStepT > 2.5f) { Shot(TEXT("07_lab_outside")); if (const FPBXDoor* D = DoorById(TEXT("lab"))) UseDoor(*D, true); AutoNext(); } break;
	case 9: if (Idle() && AutoStepT > 1.5f) { Shot(TEXT("08_lab_inside")); if (APBXNPC* V = NPCs.FindRef(TEXT("vale"))) { TeleportPlayer(V->GetActorLocation() + V->GetActorForwardVector() * 170.f, 0); TalkTo(V); } AutoNext(); } break;
	case 10: if (UI->Mode == EPBXUIMode::Choice && AutoStepT > 1.5f) { Shot(TEXT("09_starter_choice")); InNav(1, 0); AutoNext(); } break;
	case 11: if (AutoStepT > .8f) { InConfirm(); AutoNext(); } break;
	case 12: if (Idle() && Step() == EPBXStep::Capture) { Shot(TEXT("10_partner")); AutoNext(); } break;
	case 13: if (AutoStepT > 1.f) { if (const FPBXDoor* D = DoorById(TEXT("lab"))) UseDoor(*D, false); AutoNext(); } break;
	case 14: if (Idle() && AutoStepT > 1.f)
		{
			Shot(TEXT("11_outside_partner"));
			if (Grass.Num()) { const FVector2D C = Grass[0].GetCenter(); TeleportPlayer(FVector(C.X + 900.f, C.Y, 0), 180.f); }
			AutoNext();
		} break;
	case 15: if (AutoStepT > 3.f && Idle()) { Shot(TEXT("12_tall_grass")); APBXEcho* Best = nullptr; for (APBXEcho* W : Wilds) if (W && !W->IsHidden()) { Best = W; break; } if (Best) TeleportPlayer(Best->GetActorLocation() - FVector(400, 0, 0), 0.f); AutoNext(); } break;
	case 16: if (Bt.bActive && UI->BannerT > 0.f && AutoStepT > .6f) { Shot(TEXT("13_battle_intro")); AutoNext(); } else if (AutoStepT > 6.f && Idle()) { APBXEcho* Best = nullptr; for (APBXEcho* W : Wilds) if (W && !W->IsHidden()) { Best = W; break; } if (Best) TeleportPlayer(Best->GetActorLocation() + FVector(60, 0, 0), 0.f); AutoStepT = 0.f; } break;
	case 17: if (Bt.bActive && UI->bMoves) { Shot(TEXT("14_battle_moves")); AutoNext(); } break;
	case 18: if (Bt.bActive && UI->ShakeT > .05f) { Shot(TEXT("15_battle_hit")); AutoNext(); } else if (!Bt.bActive && AutoStepT > 2.f) AutoNext(); break;
	case 19: if (UI->BigT > 1.5f && UI->BigTitle == TEXT("GOTCHA!")) { Shot(TEXT("16_gotcha")); AutoNext(); }
		else if (Idle() && Step() == EPBXStep::Capture && AutoStepT > 3.f) { AutoStep = 15; AutoStepT = 0.f; PBXLOG("[PBXAUTO] capture missed — retry"); }
		else if (Idle() && Step() >= EPBXStep::RhoBattle) AutoNext();
		break;
	case 20: if (Idle() && Step() == EPBXStep::RhoBattle) { if (APBXNPC* R = NPCs.FindRef(TEXT("rho"))) { TeleportPlayer(R->GetActorLocation() + R->GetActorForwardVector() * 180.f, 0); TalkTo(R); } AutoNext(); } break;
	case 21: if (Bt.bActive && UI->bMoves) { Shot(TEXT("17_rival_battle")); AutoNext(); } break;
	case 22: if (!Bt.bActive && UI->Mode == EPBXUIMode::Dialogue && AutoStepT > 1.f) { Shot(TEXT("18_after_rival")); AutoNext(); } break;
	case 23: if (Idle())
		{
			if (Step() != EPBXStep::Rest) { PBXLOG("[PBXAUTO] rival battle lost, retrying after rest (step %d)", (int32)Step()); }
			if (const FPBXDoor* D = DoorById(TEXT("house"))) { FPBXSpot S = D->Inside; PlacePlayer(S); TeleportPlayer(BedPos + FVector(0, -120, 0), 0.f); }
			AutoNext();
		} break;
	case 24: if (AutoStepT > 1.f && Idle()) { Rest(); AutoNext(); } break;
	case 25: if (Idle() && AutoStepT > 2.f)
		{
			Shot(TEXT("19_rested"));
			if (Step() == EPBXStep::RhoBattle) { AutoStep = 20; AutoStepT = 0.f; break; }
			if (Step() != EPBXStep::Gate) { Fail(TEXT("expected Gate step after rest")); break; }
			PlacePlayer(TrainBoard); AutoNext();
		} break;
	case 26: if (AutoStepT > 2.f && Idle()) { Shot(TEXT("20_station")); FindNearest(); if (NearKind == EKind::Train) Interact(); else { Fail(TEXT("train not in reach")); BoardTrain(); } AutoNext(); } break;
	case 27: { static bool bTrainShot = false; if (bTrainGo && !bTrainShot && TrainV > 900.f) { bTrainShot = true; Shot(TEXT("21_train_departs")); } }
		if (Menu == EMenu::Complete && AutoStepT > 1.f) { Shot(TEXT("21b_chapter_complete")); AutoNext(); }
		else if (UI->Mode == EPBXUIMode::Dialogue && AutoStepT > .8f) InConfirm();
		break;
	case 28:
	{
		// save -> new game -> load must give the same progress back
		SaveNow(false); const int32 Before = (int32)Step(); const int32 Caught = Game->State->Captures;
		Game->NewGame(true); const bool bOk = Game->Load() && (int32)Step() == Before && Game->State->Captures == Caught;
		PBXLOG("[PBXAUTO] save/load %s (step %d, captures %d)", bOk ? TEXT("ok") : TEXT("FAILED"), (int32)Step(), Game->State->Captures);
		if (!bOk) bAutoFail = true;
		CloseChoice(); Menu = EMenu::None; TeleportPlayer(FVector(0, -1000, 0), -90.f);
		AutoNext(); break;
	}
	case 29: if (AutoStepT > 3.f) { Shot(TEXT("22_town_day")); AutoNext(); } break;
	case 30: if (AutoStepT > 2.f) { PBXLOG("[PBXAUTO] %s — %d screenshots", bAutoFail ? TEXT("DONE WITH FAILURES") : TEXT("PASS"), AutoShots); AutoNext(); } break;
	case 31: if (AutoStepT > 2.f) { FPlatformMisc::RequestExit(false); AutoNext(); } break;
	default: break;
	}
}

// =================================================================== game mode + controller
APBXGameMode::APBXGameMode()
{
	DefaultPawnClass = APBXPlayer::StaticClass();
	PlayerControllerClass = APBXController::StaticClass();
}

void APBXGameMode::BeginPlay()
{
	Super::BeginPlay();
	FActorSpawnParameters P; P.Name = TEXT("PBX_Director");
	GetWorld()->SpawnActor<APBXDirector>(APBXDirector::StaticClass(), FTransform::Identity, P);
}

UInputAction* APBXController::MakeAction(FName N, bool bAxis2D, bool bAxis1D)
{
	UInputAction* A = NewObject<UInputAction>(this, N);
	A->ValueType = bAxis2D ? EInputActionValueType::Axis2D : bAxis1D ? EInputActionValueType::Axis1D : EInputActionValueType::Boolean;
	Actions.Add(A); return A;
}

void APBXController::SetupInputComponent()
{
	Super::SetupInputComponent();
	IMC = NewObject<UInputMappingContext>(this, TEXT("IMC_PBX"));
	UInputAction* Move = MakeAction(TEXT("IA_Move"), true), * Look = MakeAction(TEXT("IA_Look"), true), * Jump = MakeAction(TEXT("IA_Jump"), false);
	UInputAction* Confirm = MakeAction(TEXT("IA_Confirm"), false), * Back = MakeAction(TEXT("IA_Back"), false), * Pause = MakeAction(TEXT("IA_Pause"), false);
	UInputAction* Run = MakeAction(TEXT("IA_Run"), false), * Zoom = MakeAction(TEXT("IA_Zoom"), false, true);
	UInputAction* Up = MakeAction(TEXT("IA_Up"), false), * Down = MakeAction(TEXT("IA_Down"), false), * Left = MakeAction(TEXT("IA_Left"), false), * Right = MakeAction(TEXT("IA_Right"), false);
	auto Map = [this](UInputAction* A, FKey K, bool bSwizzle = false, bool bNegX = false, bool bNegY = false, float Scale = 1.f)
	{
		FEnhancedActionKeyMapping& M = IMC->MapKey(A, K);
		if (bSwizzle) { UInputModifierSwizzleAxis* S = NewObject<UInputModifierSwizzleAxis>(this); M.Modifiers.Add(S); }
		if (bNegX || bNegY) { UInputModifierNegate* N = NewObject<UInputModifierNegate>(this); N->bX = bNegX; N->bY = bNegY; N->bZ = false; M.Modifiers.Add(N); }
		if (Scale != 1.f) { UInputModifierScalar* S = NewObject<UInputModifierScalar>(this); S->Scalar = FVector(Scale, Scale, Scale); M.Modifiers.Add(S); }
	};
	Map(Move, EKeys::W, true); Map(Move, EKeys::S, true, true); Map(Move, EKeys::A, false, true); Map(Move, EKeys::D); Map(Move, EKeys::Gamepad_Left2D);
	Map(Look, EKeys::Mouse2D, false, false, true, .5f); Map(Look, EKeys::Gamepad_Right2D, false, false, true, 2.2f);
	Map(Jump, EKeys::SpaceBar);
	for (FKey K : { EKeys::E, EKeys::Enter, EKeys::F, EKeys::Gamepad_FaceButton_Bottom }) Map(Confirm, K);
	for (FKey K : { EKeys::BackSpace, EKeys::Gamepad_FaceButton_Right }) Map(Back, K);
	for (FKey K : { EKeys::Escape, EKeys::P, EKeys::Gamepad_Special_Right }) Map(Pause, K);
	for (FKey K : { EKeys::LeftShift, EKeys::Gamepad_LeftTrigger, EKeys::Gamepad_LeftThumbstick }) Map(Run, K);
	Map(Zoom, EKeys::MouseWheelAxis); Map(Zoom, EKeys::Gamepad_RightShoulder); Map(Zoom, EKeys::Gamepad_LeftShoulder, false, true);
	for (FKey K : { EKeys::Up, EKeys::Gamepad_DPad_Up, EKeys::W }) Map(Up, K);
	for (FKey K : { EKeys::Down, EKeys::Gamepad_DPad_Down, EKeys::S }) Map(Down, K);
	for (FKey K : { EKeys::Left, EKeys::Gamepad_DPad_Left, EKeys::A }) Map(Left, K);
	for (FKey K : { EKeys::Right, EKeys::Gamepad_DPad_Right, EKeys::D }) Map(Right, K);
	TArray<UInputAction*> Nums;
	const FKey NumKeys[7] = { EKeys::One, EKeys::Two, EKeys::Three, EKeys::Four, EKeys::Five, EKeys::Six, EKeys::Seven };
	for (int32 i = 0; i < 7; i++) { UInputAction* A = MakeAction(FName(*FString::Printf(TEXT("IA_Num%d"), i + 1)), false); Map(A, NumKeys[i]); Nums.Add(A); }
	if (UEnhancedInputLocalPlayerSubsystem* Sub = ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(GetLocalPlayer())) Sub->AddMappingContext(IMC, 0);
	UEnhancedInputComponent* EI = Cast<UEnhancedInputComponent>(InputComponent);
	if (!EI) { UE_LOG(LogPBX, Error, TEXT("[PBX] no enhanced input component")); return; }
	auto D = [this]() { return Director.Get(); };
	EI->BindActionValueLambda(Move, ETriggerEvent::Triggered, [D](const FInputActionValue& V) { if (APBXDirector* X = D()) X->InMove(V.Get<FVector2D>()); });
	EI->BindActionValueLambda(Look, ETriggerEvent::Triggered, [D](const FInputActionValue& V) { if (APBXDirector* X = D()) X->InLook(V.Get<FVector2D>()); });
	EI->BindActionValueLambda(Jump, ETriggerEvent::Started, [D](const FInputActionValue&) { if (APBXDirector* X = D()) X->InJump(); });
	EI->BindActionValueLambda(Confirm, ETriggerEvent::Started, [D](const FInputActionValue&) { if (APBXDirector* X = D()) X->InConfirm(); });
	EI->BindActionValueLambda(Back, ETriggerEvent::Started, [D](const FInputActionValue&) { if (APBXDirector* X = D()) X->InBack(); });
	EI->BindActionValueLambda(Pause, ETriggerEvent::Started, [D](const FInputActionValue&) { if (APBXDirector* X = D()) X->InPause(); });
	EI->BindActionValueLambda(Run, ETriggerEvent::Started, [D](const FInputActionValue&) { if (APBXDirector* X = D()) X->InRun(true); });
	EI->BindActionValueLambda(Run, ETriggerEvent::Completed, [D](const FInputActionValue&) { if (APBXDirector* X = D()) X->InRun(false); });
	EI->BindActionValueLambda(Zoom, ETriggerEvent::Triggered, [D](const FInputActionValue& V) { if (APBXDirector* X = D()) X->InZoom(V.Get<float>()); });
	EI->BindActionValueLambda(Up, ETriggerEvent::Started, [D](const FInputActionValue&) { if (APBXDirector* X = D()) X->InNav(0, 1); });
	EI->BindActionValueLambda(Down, ETriggerEvent::Started, [D](const FInputActionValue&) { if (APBXDirector* X = D()) X->InNav(0, -1); });
	EI->BindActionValueLambda(Left, ETriggerEvent::Started, [D](const FInputActionValue&) { if (APBXDirector* X = D()) X->InNav(-1, 0); });
	EI->BindActionValueLambda(Right, ETriggerEvent::Started, [D](const FInputActionValue&) { if (APBXDirector* X = D()) X->InNav(1, 0); });
	for (int32 i = 0; i < Nums.Num(); i++) EI->BindActionValueLambda(Nums[i], ETriggerEvent::Started, [D, i](const FInputActionValue&) { if (APBXDirector* X = D()) X->InNumber(i + 1); });
}

void APBXController::PlayerTick(float Dt)
{
	Super::PlayerTick(Dt);
	const bool bCursor = Director.IsValid() && Director->WantsCursor();
	if (bCursor != bShowMouseCursor)
	{
		bShowMouseCursor = bCursor;
		if (bCursor) { FInputModeGameAndUI M; M.SetHideCursorDuringCapture(false); M.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock); SetInputMode(M); }
		else SetInputMode(FInputModeGameOnly());
	}
}
