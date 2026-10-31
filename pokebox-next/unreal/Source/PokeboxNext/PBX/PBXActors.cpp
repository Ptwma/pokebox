#include "PBX/PBXActors.h"
#include "GroomComponent.h"
#include "GroomAsset.h"
#include "GroomBindingAsset.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "PBX/PBXAnim.h"
#include "PBX/PBXCore.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/TextRenderComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Animation/AnimSequence.h"
#include "Engine/StaticMesh.h"
#include "Engine/Texture2D.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/SpringArmComponent.h"
#include "Camera/CameraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "AIController.h"
#include "Dom/JsonObject.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

int32 GPBXMissingAssets = 0;

// The Quaternius glTF characters face +Y after import; Unreal characters face +X.
static const float PBX_MESH_YAW = -90.f;
static const float PBX_CAPSULE_HALF = 90.f;

float PBXWorld::GroundZ(const UWorld* W, const FVector& P, float Up, float Down, float Fallback)
{
	if (!W) return Fallback;
	FHitResult H;
	FCollisionQueryParams Q(SCENE_QUERY_STAT(PBXGround), true);
	if (W->LineTraceSingleByObjectType(H, P + FVector(0, 0, Up), P - FVector(0, 0, Down), FCollisionObjectQueryParams(ECC_WorldStatic), Q)) return H.ImpactPoint.Z;
	return Fallback;
}

// ------------------------------------------------------------------ characters
APBXCharacterBase::APBXCharacterBase()
{
	PrimaryActorTick.bCanEverTick = true;
	GetCapsuleComponent()->InitCapsuleSize(34.f, PBX_CAPSULE_HALF);
	GetMesh()->SetRelativeLocationAndRotation(FVector(0, 0, -PBX_CAPSULE_HALF), FRotator(0, PBX_MESH_YAW, 0));
	GetMesh()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	GetMesh()->bRenderCustomDepth = false;
	Eyes = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("Eyes")); Eyes->SetupAttachment(GetMesh());
	Brows = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("Brows")); Brows->SetupAttachment(GetMesh());
	Hair = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("Hair")); Hair->SetupAttachment(GetMesh());
	Clothes = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("Clothes")); Clothes->SetupAttachment(GetMesh());
	for (USkeletalMeshComponent* C : { Eyes.Get(), Brows.Get(), Hair.Get(), Clothes.Get() }) C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	bUseControllerRotationYaw = false;
	UCharacterMovementComponent* M = GetCharacterMovement();
	M->bOrientRotationToMovement = true; M->RotationRate = FRotator(0, 600, 0);
	M->MaxWalkSpeed = 170.f; M->BrakingDecelerationWalking = 1600.f; M->JumpZVelocity = 460.f; M->AirControl = .4f;
	M->MaxStepHeight = 50.f; M->SetWalkableFloorAngle(50.f);
	AutoPossessAI = EAutoPossessAI::PlacedInWorldOrSpawned;
	AIControllerClass = AAIController::StaticClass();
}

UPBXAnimInstance* APBXCharacterBase::Anim() const { return Cast<UPBXAnimInstance>(GetMesh()->GetAnimInstance()); }

bool APBXCharacterBase::ApplyMetaHuman(const FString& Id)
{
	static TSharedPtr<FJsonObject> Manifest;
	if (!Manifest.IsValid())
	{
		FString Txt;
		if (FFileHelper::LoadFileToString(Txt, *(FPaths::ProjectContentDir() / TEXT("PBX/Data/mh_manifest.json"))))
		{
			TSharedRef<TJsonReader<>> R = TJsonReaderFactory<>::Create(Txt); FJsonSerializer::Deserialize(R, Manifest);
		}
		if (!Manifest.IsValid()) Manifest = MakeShared<FJsonObject>();
	}
	const TSharedPtr<FJsonObject>* E = nullptr;
	if (!Manifest->TryGetObjectField(Id, E)) { UE_LOG(LogTemp, Warning, TEXT("[PBX] MetaHuman %s not in the manifest"), *Id); return false; }
	auto LoadPath = [](const FString& P) -> UObject* { const FString N = FPaths::GetBaseFilename(P); return StaticLoadObject(UObject::StaticClass(), nullptr, *(P + TEXT(".") + N)); };
	USkeletalMesh* Body = Cast<USkeletalMesh>(LoadPath((*E)->GetStringField(TEXT("body"))));
	if (!Body) { UE_LOG(LogTemp, Warning, TEXT("[PBX] MetaHuman %s body missing"), *Id); return false; }
	for (USceneComponent* P : MHParts) if (P) P->DestroyComponent();
	MHParts.Reset();
	GetMesh()->SetSkeletalMesh(Body); GetMesh()->EmptyOverrideMaterials();
	GetMesh()->SetAnimationMode(EAnimationMode::AnimationBlueprint); GetMesh()->SetAnimInstanceClass(UPBXAnimInstance::StaticClass());
	GetMesh()->SetRelativeScale3D(FVector(1.f));
	for (USkeletalMeshComponent* X : { Eyes.Get(), Brows.Get(), Hair.Get(), Clothes.Get() }) { X->SetSkeletalMesh(nullptr); X->SetVisibility(false); }
	USkeletalMeshComponent* Face = nullptr;
	for (const TSharedPtr<FJsonValue>& V : (*E)->GetArrayField(TEXT("parts")))
	{
		const TSharedPtr<FJsonObject> O = V->AsObject();
		USkeletalMesh* M = Cast<USkeletalMesh>(LoadPath(O->GetStringField(TEXT("mesh")))); if (!M) continue;
		USkeletalMeshComponent* C = NewObject<USkeletalMeshComponent>(this, FName(*(TEXT("MH_") + O->GetStringField(TEXT("name")))));
		C->SetupAttachment(GetMesh()); C->RegisterComponent(); C->SetSkeletalMesh(M); C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		C->SetLeaderPoseComponent(GetMesh());          // follows the body (the face keeps its neutral expression: JOINTS_ONLY rig, no face anim)
		MHParts.Add(C);
		if (O->GetBoolField(TEXT("face"))) Face = C;
	}
	for (const TSharedPtr<FJsonValue>& V : (*E)->GetArrayField(TEXT("grooms")))
	{
		const TSharedPtr<FJsonObject> O = V->AsObject();
		UGroomAsset* G = Cast<UGroomAsset>(LoadPath(O->GetStringField(TEXT("groom")))); if (!G) continue;
		UGroomComponent* GC = NewObject<UGroomComponent>(this, FName(*(TEXT("MHG_") + O->GetStringField(TEXT("name")))));
		GC->SetupAttachment(Face ? Face : GetMesh());
		if (UGroomBindingAsset* B = Cast<UGroomBindingAsset>(LoadPath(O->GetStringField(TEXT("binding"))))) GC->SetBindingAsset(B);
		GC->SetGroomAsset(G); GC->RegisterComponent(); GC->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		MHParts.Add(GC);
	}
	bMetaHuman = true;
	// kids (manifest "kid"): MetaHuman has no child body (height floor 1.36 m) → a slightly larger head reads younger;
	// shorter bodies step faster at the same speed (StrideScale; the _MH clips were retargeted on a 1.36–1.4 m body)
	double Hgt = 170.0; (*E)->TryGetNumberField(TEXT("height"), Hgt);
	bool bKid = false; (*E)->TryGetBoolField(TEXT("kid"), bKid);
	bKidMH = bKid; MHHeight = (float)Hgt;
	if (UPBXAnimInstance* A = Anim())
	{
		A->SetSuffix(TEXT("_MH")); A->Style = FPBXStyle();
		if (bKid) { A->Style.Head = 1.09f; A->Style.Hand = .96f; }
		A->StrideScale = (float)Hgt / 172.f;
	}
	return true;
}

void APBXCharacterBase::ApplyLook(const FString& BodyKind, const FString& HairName, float Scale, const FString& Outfit, FLinearColor HairColor)
{
	// "mh:<id>": a MetaHuman (phase 5). Falls back to the old stylized look if that character isn't built yet.
	if (BodyKind.StartsWith(TEXT("mh:")) && ApplyMetaHuman(BodyKind.Mid(3))) { SetActorScale3D(FVector(1.f)); return; }
	bMetaHuman = false;
	const bool bBoy = BodyKind == TEXT("boy");
	const bool bMale = BodyKind != TEXT("f");
	bMaleLook = bMale;
	USkeletalMesh* B = nullptr;
	const FString Dir = bMale ? TEXT("/Game/PBX/Characters/Superhero_Male_FullBody/SkeletalMeshes/") : TEXT("/Game/PBX/Characters/Superhero_Female_FullBody/SkeletalMeshes/");
	auto Load = [&](const FString& N) { return LoadObject<USkeletalMesh>(nullptr, *(Dir + N + TEXT(".") + N)); };
	if (bBoy) B = LoadObject<USkeletalMesh>(nullptr, TEXT("/Game/Fab/Free_Stylized_Boy_Character/boy1.boy1"));
	if (!B) B = Load(bMale ? TEXT("SuperHero_Male") : TEXT("Superhero_Female"));
	const bool bQ = !bBoy || !B || !B->GetPathName().Contains(TEXT("Stylized_Boy"));
	if (B)
	{
		GetMesh()->SetSkeletalMesh(B);
		GetMesh()->SetAnimationMode(EAnimationMode::AnimationBlueprint);
		GetMesh()->SetAnimInstanceClass(UPBXAnimInstance::StaticClass());
	}
	else UE_LOG(LogTemp, Error, TEXT("[PBX] body mesh missing (%s)"), *BodyKind);
	// the stylized boy is a child model (1.17 m): scale the mesh, keep the capsule; feet stay on the capsule bottom
	GetMesh()->SetRelativeScale3D(FVector(bQ ? 1.f : 1.42f));
	if (!bQ) GetMesh()->EmptyOverrideMaterials();   // the boy keeps his own materials (no painted outfit)
	Eyes->SetSkeletalMesh(bQ ? Load(TEXT("Eyes")) : nullptr); Brows->SetSkeletalMesh(bQ ? Load(TEXT("Eyebrows")) : nullptr);
	USkeletalMesh* H = nullptr;
	if (bQ && !HairName.IsEmpty()) H = Cast<USkeletalMesh>(PBXAssets::FindByName(TEXT("/Game/PBX/Characters/Hair"), HairName, USkeletalMesh::StaticClass()));
	Hair->SetSkeletalMesh(H); Hair->SetVisibility(H != nullptr);
	USkeletalMesh* C = nullptr;
	if (bQ && !Outfit.IsEmpty()) C = Cast<USkeletalMesh>(PBXAssets::FindByName(TEXT("/Game/PBX/Characters/Clothes"), TEXT("SK_Cloth_") + Outfit, USkeletalMesh::StaticClass()));
	if (bQ && !Outfit.IsEmpty() && !C) { GPBXMissingAssets++; UE_LOG(LogTemp, Warning, TEXT("[PBXASSET] clothes SK_Cloth_%s missing (%s)"), *Outfit, *GetName()); }
	Clothes->SetSkeletalMesh(C); Clothes->SetVisibility(C != nullptr);
	if (C)
		if (UMaterialInterface* CM = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/PBX/Materials/M_PBX_Cloth.M_PBX_Cloth")))
		{
			const FString PN = TEXT("T_ClothPal_") + Outfit;
			UTexture2D* Pal = LoadObject<UTexture2D>(nullptr, *FString::Printf(TEXT("/Game/PBX/Characters/Clothes/Pal/%s.%s"), *PN, *PN));
			for (int32 i = 0; i < Clothes->GetNumMaterials(); i++)
			{
				UMaterialInstanceDynamic* D = UMaterialInstanceDynamic::Create(CM, Clothes);
				if (Pal) D->SetTextureParameterValue(TEXT("Pal"), Pal);
				Clothes->SetMaterial(i, D);
			}
		}
	for (USkeletalMeshComponent* X : { Eyes.Get(), Brows.Get(), Hair.Get(), Clothes.Get() }) X->SetLeaderPoseComponent(GetMesh());
	// body paint under the clothes (tools/outfits.py): same palette, so seams between garments never show bare skin
	if (bQ && !Outfit.IsEmpty())
	{
		const FString N = TEXT("T_Outfit_") + Outfit;
		if (UTexture2D* T = LoadObject<UTexture2D>(nullptr, *FString::Printf(TEXT("/Game/PBX/Characters/Outfits/%s.%s"), *N, *N)))
		{
			if (UMaterialInstanceDynamic* MID = GetMesh()->CreateAndSetMaterialInstanceDynamic(0)) MID->SetTextureParameterValue(TEXT("BaseColorTexture"), T);
		}
		else { GPBXMissingAssets++; UE_LOG(LogTemp, Warning, TEXT("[PBXASSET] outfit texture %s missing (%s)"), *N, *GetName()); }
	}
	if (HairColor.A > 0.f && H)
		for (int32 i = 0; i < Hair->GetNumMaterials(); i++)
			if (UMaterialInstanceDynamic* MID = Hair->CreateAndSetMaterialInstanceDynamic(i)) MID->SetVectorParameterValue(TEXT("BaseColorFactor"), HairColor);
	SetActorScale3D(FVector(Scale));
	// cartoon proportions (council: no more bodybuilders): bigger head, hands and shoes, slim limbs, narrow chest.
	// Children (actor scale < .8) get an even bigger head.
	if (UPBXAnimInstance* A = Anim())
	{
		A->SetSuffix(bQ ? FString() : FString(TEXT("_Boy")));
		FPBXStyle S;
		if (bQ) { S.Head = Scale < .8f ? 1.5f : 1.32f; S.Hand = 1.18f; S.Foot = 1.15f; S.Limb = .76f; S.Leg = .84f; S.Chest = .86f; S.Neck = .82f; }
		A->Style = S;
	}
}

void APBXCharacterBase::PlayAction(const FString& Short, bool bLoop, float Blend) { if (UPBXAnimInstance* A = Anim()) A->PlayAction(A->Clip(Short), bLoop, Blend); }
void APBXCharacterBase::StopAction(float Blend) { if (UPBXAnimInstance* A = Anim()) A->StopAction(Blend); }
void APBXCharacterBase::SetIdleAnim(const FString& Short) { if (UPBXAnimInstance* A = Anim()) A->SetIdle(A->Clip(Short)); }

void APBXCharacterBase::FaceTowards(const FVector& P, bool bInstant)
{
	const FVector D = P - GetActorLocation(); if (D.Size2D() < 1.f) return;
	TurnYaw = D.Rotation().Yaw;
	if (bInstant) { SetActorRotation(FRotator(0, TurnYaw, 0)); bTurning = false; }
	else bTurning = true;
}

void APBXCharacterBase::Tick(float Dt)
{
	Super::Tick(Dt);
	if (bTurning)
	{
		const float Y = FMath::FixedTurn(GetActorRotation().Yaw, TurnYaw, 420.f * Dt);
		SetActorRotation(FRotator(0, Y, 0));
		if (FMath::Abs(FRotator::NormalizeAxis(Y - TurnYaw)) < 1.f) bTurning = false;
	}
}

APBXPlayer::APBXPlayer()
{
	Boom = CreateDefaultSubobject<USpringArmComponent>(TEXT("Boom"));
	Boom->SetupAttachment(RootComponent);
	Boom->TargetArmLength = 430.f; Boom->bUsePawnControlRotation = true; Boom->SocketOffset = FVector(0, 40, 60);
	Boom->bEnableCameraLag = true; Boom->CameraLagSpeed = 12.f; Boom->ProbeSize = 14.f;
	Camera = CreateDefaultSubobject<UCameraComponent>(TEXT("Camera"));
	Camera->SetupAttachment(Boom, USpringArmComponent::SocketName); Camera->bUsePawnControlRotation = false; Camera->FieldOfView = 75.f;
	GetCharacterMovement()->MaxWalkSpeed = 380.f;
	AutoPossessAI = EAutoPossessAI::Disabled;
}

void APBXPlayer::SnapCamera() { if (Boom) Boom->bEnableCameraLag = false; SnapFrames = 3; }

void APBXPlayer::Tick(float Dt)
{
	Super::Tick(Dt);
	if (SnapFrames > 0 && --SnapFrames == 0 && Boom) Boom->bEnableCameraLag = true;
}

void APBXPlayer::SetRunning(bool bRun) { bRunning = bRun; GetCharacterMovement()->MaxWalkSpeed = bRun ? 640.f : 380.f; }
void APBXPlayer::Zoom(float D) { Boom->TargetArmLength = FMath::Clamp(Boom->TargetArmLength - D * 40.f, 220.f, 760.f); }

APBXNPC::APBXNPC()
{
	Marker = CreateDefaultSubobject<UTextRenderComponent>(TEXT("Marker"));
	Marker->SetupAttachment(RootComponent);
	Marker->SetRelativeLocation(FVector(0, 0, 135)); Marker->SetHorizontalAlignment(EHTA_Center); Marker->SetVerticalAlignment(EVRTA_TextCenter);
	Marker->SetText(FText::FromString(TEXT("!"))); Marker->SetWorldSize(70.f); Marker->SetTextRenderColor(FColor(255, 214, 40));
	Marker->SetHiddenInGame(true); Marker->SetCastShadow(false);
	// keep animating while off-screen: an NPC first seen after a teleport must not pop in T-posed
	GetMesh()->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
}

void APBXNPC::SetMarker(bool bOn) { Marker->SetHiddenInGame(!bOn); }

void APBXNPC::ReturnToIdle()
{
	StopAction(.3f);
	if (!IdleAnim.IsEmpty() && IdleAnim != TEXT("Idle_Loop")) PlayAction(IdleAnim, true, .4f);
	TurnYaw = HomeYaw; bTurning = true;
}

void APBXNPC::WalkTo(const FVector& G, TFunction<void()> Done)
{
	StopAction(.2f); bWalking = true; WalkGoal = G; WalkDone = MoveTemp(Done); WalkT = 0.f;
}

void APBXNPC::Tick(float Dt)
{
	Super::Tick(Dt);
	if (!Marker->bHiddenInGame)
	{
		Marker->SetRelativeLocation(FVector(0, 0, 135 + 8 * FMath::Sin(GetWorld()->TimeSeconds * 4.f)));
		if (APlayerCameraManager* PC = UGameplayStatics::GetPlayerCameraManager(this, 0))
			Marker->SetWorldRotation(FRotator(0, (PC->GetCameraLocation() - Marker->GetComponentLocation()).Rotation().Yaw, 0));
	}
	if (bWalking)
	{
		WalkT += Dt;
		const FVector D = WalkGoal - GetActorLocation();
		if (D.Size2D() < 70.f || WalkT > 14.f)
		{
			bWalking = false;
			if (WalkT > 14.f) SetActorLocation(WalkGoal + FVector(0, 0, PBX_CAPSULE_HALF), false, nullptr, ETeleportType::TeleportPhysics);
			GetCharacterMovement()->StopMovementImmediately();
			if (WalkDone) { TFunction<void()> F = MoveTemp(WalkDone); F(); }
		}
		else AddMovementInput(FVector(D.X, D.Y, 0).GetSafeNormal(), 1.f);
	}
}

// ------------------------------------------------------------------ Echoes
APBXEcho::APBXEcho()
{
	PrimaryActorTick.bCanEverTick = true;
	Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root")); SetRootComponent(Root);
	Pivot = CreateDefaultSubobject<USceneComponent>(TEXT("Pivot")); Pivot->SetupAttachment(Root);
	Paper = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Paper")); Paper->SetupAttachment(Pivot);
	Paper->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Paper->SetRelativeRotation(FRotator(0, -90.f, 0));   // SM_EchoCard faces +Y -> turn it to face +X (the pivot looks at the camera)
	Paper->bRenderCustomDepth = false;
	Body = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("Body")); Body->SetupAttachment(Pivot);
	Body->SetCollisionEnabled(ECollisionEnabled::NoCollision); Body->SetVisibility(false);
	Body->SetAnimationMode(EAnimationMode::AnimationSingleNode);
	Body->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::OnlyTickPoseWhenRendered;
}

bool APBXEcho::SetupCreature(const FPBXCardDef* C, float Height)
{
	static TSharedPtr<FJsonObject> Man;
	if (!Man.IsValid())
	{
		FString Txt; Man = MakeShared<FJsonObject>();
		if (FFileHelper::LoadFileToString(Txt, *(FPaths::ProjectContentDir() / TEXT("PBX/Data/creatures.json"))))
		{ TSharedPtr<FJsonObject> J; const TSharedRef<TJsonReader<>> R = TJsonReaderFactory<>::Create(Txt); if (FJsonSerializer::Deserialize(R, J) && J.IsValid()) Man = J; }
	}
	const TSharedPtr<FJsonObject>* Types = nullptr; const TSharedPtr<FJsonObject>* Cre = nullptr;
	if (!C || !Man->TryGetObjectField(TEXT("types"), Types) || !Man->TryGetObjectField(TEXT("creatures"), Cre)) return false;
	const TSharedPtr<FJsonObject>* Pool = nullptr;
	if (!(*Types)->TryGetObjectField(C->Type, Pool)) (*Types)->TryGetObjectField(TEXT("Colorless"), Pool);
	if (!Pool) return false;
	// strong cards take the big / evolved form; the same card always gets the same creature
	const bool bBig = C->HP >= 90 || C->Rarity >= 3;
	TArray<FString> Keys; (*Pool)->TryGetStringArrayField(bBig ? TEXT("big") : TEXT("small"), Keys);
	if (!Keys.Num()) (*Pool)->TryGetStringArrayField(bBig ? TEXT("small") : TEXT("big"), Keys);
	TArray<FString> Ok; for (const FString& K : Keys) if ((*Cre)->HasField(K)) Ok.Add(K);
	if (!Ok.Num()) return false;
	const FString Key = Ok[GetTypeHash(C->Id) % Ok.Num()];
	const TSharedPtr<FJsonObject> E = (*Cre)->GetObjectField(Key);
	auto LoadP = [](const FString& P) -> UObject* { const FString N = FPaths::GetBaseFilename(P); return StaticLoadObject(UObject::StaticClass(), nullptr, *(P + TEXT(".") + N)); };
	USkeletalMesh* SM = Cast<USkeletalMesh>(LoadP(E->GetStringField(TEXT("mesh"))));
	if (!SM) return false;
	Clips.Reset();
	const TSharedPtr<FJsonObject>* An = nullptr;
	if (E->TryGetObjectField(TEXT("anims"), An))
		for (const auto& KV : (*An)->Values) if (UAnimSequence* S = Cast<UAnimSequence>(LoadP(KV.Value->AsString()))) Clips.Add(FName(*KV.Key), S);
	CreatureKey = Key; bFly = E->GetBoolField(TEXT("fly"));
	const float MeshH = FMath::Max(10.f, (float)E->GetNumberField(TEXT("height")));
	const float S = Height * (bFly ? .8f : 1.f) / MeshH;
	Body->SetSkeletalMesh(SM); Body->SetVisibility(true); Paper->SetVisibility(false);
	Body->SetRelativeScale3D(FVector(S)); Body->SetRelativeRotation(FRotator(0.f, -90.f, 0.f));   // glTF front (+Y after import) → actor +X
	Body->SetRelativeLocation(FVector(0.f, 0.f, bFly ? Height * .45f : 0.f));                      // flyers hover
	bCreature = true; CurClip = NAME_None; ClipLock = 0.f; PlayClip(TEXT("idle"), true);
	return true;
}

void APBXEcho::PlayClip(FName Role, bool bLoop, float Lock)
{
	if (!bCreature) return;
	TObjectPtr<UAnimSequence>* A = Clips.Find(Role);
	if (!A || !*A) { if (Role != TEXT("idle")) PlayClip(TEXT("idle"), true); return; }
	if (CurClip == Role && bLoop && Lock <= 0.f) return;
	Body->PlayAnimation(*A, bLoop); CurClip = Role; ClipLock = Lock;
}

bool APBXEcho::Setup(FName Card, float Height)
{
	CardId = Card; HeightCm = Height;
	UStaticMesh* M = LoadObject<UStaticMesh>(nullptr, TEXT("/Game/PBX/Meshes/SM_EchoCard.SM_EchoCard"));
	UMaterialInterface* Mat = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/PBX/Materials/M_PBX_Echo.M_PBX_Echo"));
	const FPBXCardDef* C = PBXData::Card(Card);
	UTexture2D* Tex = C ? LoadObject<UTexture2D>(nullptr, *C->EchoTexturePath()) : nullptr;
	if (!M || !Mat || !Tex) { GPBXMissingAssets++; UE_LOG(LogTemp, Error, TEXT("[PBX] echo assets missing for %s (mesh %d mat %d tex %d)"), *Card.ToString(), M != nullptr, Mat != nullptr, Tex != nullptr); }
	if (SetupCreature(C, Height)) return true;
	bCreature = false; Body->SetVisibility(false); Paper->SetVisibility(true);
	if (M) Paper->SetStaticMesh(M);
	if (Mat) { MID = UMaterialInstanceDynamic::Create(Mat, this); if (Tex) MID->SetTextureParameterValue(TEXT("Tex"), Tex); Paper->SetMaterial(0, MID); }
	// visible-art normalisation (council S9): cut-outs have transparent margins of every size, so a wide Rattata read small
	// and birds floated above their battle base. Content/PBX/Data/echo_bounds.json holds each cut-out's opaque box
	// (u0, v0, u1, v1; v from the top) -> scale the art so its visible size matches Height and put its lowest pixel on the ground.
	static TMap<FName, FVector4> Bounds; static bool bLoaded = false;
	if (!bLoaded)
	{
		bLoaded = true; FString Txt;
		if (FFileHelper::LoadFileToString(Txt, *(FPaths::ProjectContentDir() / TEXT("PBX/Data/echo_bounds.json"))))
		{
			TSharedPtr<FJsonObject> J; const TSharedRef<TJsonReader<>> R = TJsonReaderFactory<>::Create(Txt);
			if (FJsonSerializer::Deserialize(R, J) && J.IsValid())
				for (const auto& KV : J->Values)
				{
					const TArray<TSharedPtr<FJsonValue>>* A = nullptr;
					if (KV.Value->TryGetArray(A) && A->Num() == 4) Bounds.Add(FName(KV.Key), FVector4((*A)[0]->AsNumber(), (*A)[1]->AsNumber(), (*A)[2]->AsNumber(), (*A)[3]->AsNumber()));
				}
		}
	}
	float S = Height / 100.f; float Lift = 0.f;
	if (const FVector4* B = Bounds.Find(Card); B && M)
	{
		const FBox MB = M->GetBoundingBox(); const FVector E = MB.GetSize();
		const float MeshH = E.Z, MeshW = FMath::Max(E.X, E.Y);
		const float VisH = FMath::Max(.05f, float(B->W - B->Y)) * MeshH, VisW = FMath::Max(.05f, float(B->Z - B->X)) * MeshW;
		S = .9f * Height / FMath::Sqrt(VisH * VisW);   // same visible AREA for every Echo (wide Rattata grows, tall Kakuna shrinks); .9 ~ a typical cut-out, so average sizes stay
		Lift = -(MB.Min.Z + (1.f - float(B->W)) * MeshH) * S;     // the lowest opaque pixel touches the ground
	}
	Paper->SetRelativeScale3D(FVector(S));
	Paper->SetRelativeLocation(FVector(0, 0, Lift));
	return M && Mat && Tex;
}

void APBXEcho::PlaceAt(const FVector& P)
{
	SetActorLocation(FVector(P.X, P.Y, PBXWorld::GroundZ(GetWorld(), P, 300.f, 1500.f, P.Z)));
}

void APBXEcho::Flash(const FLinearColor& C, float S) { FlashT = .35f; FlashCol = C; FlashStrength = S; }
void APBXEcho::Lunge(const FVector& Dir, float Dist) { LungeT = 0.f; LungeDir = Dir.GetSafeNormal2D(); LungeDist = Dist; PlayClip(TEXT("attack"), false, .9f); }
void APBXEcho::Hurt() { HurtT = 0.f; Flash(FLinearColor(1, .25f, .2f), 2.5f); PlayClip(TEXT("hit"), false, .55f); }
void APBXEcho::SetFaint(bool b) { bFaint = b; if (!b) { FaintK = 0.f; ClipLock = 0.f; CurClip = NAME_None; } else PlayClip(TEXT("death"), false, 1e6f); }
void APBXEcho::PopIn() { PopT = 0.f; PlayClip(TEXT("happy"), false, 1.1f); }

void APBXEcho::Tick(float Dt)
{
	Super::Tick(Dt);
	T += Dt;
	const UWorld* W = GetWorld();
	FVector Loc = GetActorLocation(); float Moving = 0.f;
	auto StepTowards = [&](const FVector& Target, float MaxSpeed)
	{
		FVector D = Target - Loc; D.Z = 0; const float Dist = D.Size();
		if (Dist > 5.f)
		{
			const float Sp = FMath::Min(MaxSpeed, Dist * 3.f);
			Loc += D / Dist * FMath::Min(Dist, Sp * Dt); Moving = FMath::Clamp(Sp / 250.f, 0.f, 1.f);
		}
		Loc.Z = PBXWorld::GroundZ(W, Loc, 200.f, 600.f, Loc.Z);
	};
	if (!bFaint)
	{
		if (Mode == EMode::Follow && FollowTarget.IsValid())
		{
			const AActor* A = FollowTarget.Get();
			const FVector Want = A->GetActorLocation() - A->GetActorForwardVector() * 20.f + A->GetActorRightVector() * 150.f;   // beside you, not between you and the camera
			const float Dist = FVector::Dist2D(Want, Loc);
			if (Dist > 900.f) Loc = FVector(Want.X, Want.Y, PBXWorld::GroundZ(W, Want, 300.f, 1500.f, Loc.Z)); // teleported (doors)
			else if (Dist > 60.f) StepTowards(Want, FMath::Clamp(Dist * 2.2f, 150.f, 700.f));
		}
		else if (Mode == EMode::Wander)
		{
			if (WanderWait > 0.f) WanderWait -= Dt;
			else
			{
				if (FVector::Dist2D(Goal, Loc) < 20.f || Goal.IsZero())
				{
					Goal = FVector(FMath::FRandRange(WanderBox.Min.X, WanderBox.Max.X), FMath::FRandRange(WanderBox.Min.Y, WanderBox.Max.Y), Loc.Z);
					WanderWait = FMath::FRandRange(.8f, 3.f);
				}
				else StepTowards(Goal, 120.f);
			}
		}
	}
	SetActorLocation(Loc);
	if (bCreature)
	{
		// a creature: turns to where it walks (else to its opponent / the camera), animation clip from the state
		const FVector V = (Loc - PrevLoc) / FMath::Max(Dt, 1e-3f); PrevLoc = Loc; const float Sp = V.Size2D();
		float Want = CurYaw;
		if (Sp > 20.f) Want = V.Rotation().Yaw;
		else if (Mode == EMode::Stage && !FaceAt.IsZero()) Want = (FaceAt - Loc).Rotation().Yaw;
		else if (APlayerCameraManager* PC = UGameplayStatics::GetPlayerCameraManager(this, 0)) Want = (PC->GetCameraLocation() - Loc).Rotation().Yaw;
		CurYaw = FMath::FixedTurn(CurYaw, Want, 360.f * Dt);
		ClipLock -= Dt;
		if (!bFaint && ClipLock <= 0.f) PlayClip(Sp > 330.f ? TEXT("run") : Sp > 25.f ? TEXT("walk") : TEXT("idle"), true);
		FVector Off(0, 0, bFly ? 10.f * FMath::Sin(T * 2.2f) : 0.f);
		if (LungeT >= 0.f) { LungeT += Dt; const float k = LungeT / .45f; if (k >= 1.f) LungeT = -1.f; else Off += LungeDir * LungeDist * FMath::Sin(k * PI); }
		if (HurtT >= 0.f) { HurtT += Dt; if (HurtT > .35f) HurtT = -1.f; else Off += FVector(FMath::Sin(HurtT * 90.f) * 5.f, FMath::Cos(HurtT * 77.f) * 5.f, 0); }
		PopT = FMath::Min(1.f, PopT + Dt / .4f);
		const float Pop = PopT >= 1.f ? 1.f : FMath::Sin(PopT * PI * .5f) * (1.f + .2f * FMath::Sin(PopT * PI));
		Pivot->SetRelativeLocation(Off);
		Pivot->SetWorldRotation(FRotator(0.f, CurYaw, 0.f));
		Pivot->SetRelativeScale3D(FVector(Pop));
		return;
	}

	// face the camera (a paper figure turning to look at you)
	if (APlayerCameraManager* PC = UGameplayStatics::GetPlayerCameraManager(this, 0))
	{
		const float Want = (PC->GetCameraLocation() - Loc).Rotation().Yaw;
		CurYaw = FMath::FixedTurn(CurYaw, Want, 720.f * Dt);
	}
	// hop / breathe / squash, lunge, hurt shake, pop-in, faint
	HopT += Dt * (6.f + 8.f * Moving);
	const float Hop = FMath::Abs(FMath::Sin(HopT * 1.6f)) * (6.f + 26.f * Moving);
	const float Breath = 1.f + .025f * FMath::Sin(T * 3.1f);
	FVector Off(0, 0, Hop);
	if (LungeT >= 0.f)
	{
		LungeT += Dt; const float k = LungeT / .38f;
		if (k >= 1.f) LungeT = -1.f; else Off += LungeDir * LungeDist * FMath::Sin(k * PI);
	}
	if (HurtT >= 0.f)
	{
		HurtT += Dt; if (HurtT > .35f) HurtT = -1.f; else Off += FVector(FMath::Sin(HurtT * 90.f) * 9.f, FMath::Cos(HurtT * 77.f) * 9.f, 0);
	}
	PopT = FMath::Min(1.f, PopT + Dt / .4f);
	const float Pop = PopT >= 1.f ? 1.f : FMath::Sin(PopT * PI * .5f) * (1.f + .25f * FMath::Sin(PopT * PI));
	FaintK = FMath::FInterpTo(FaintK, bFaint ? 1.f : 0.f, Dt, 5.f);
	// paper reactions (council S9): a hit tips the card back like a flicked postcard; fainting drops it flat on its back;
	// a send-out slides it in from the side with a quarter spin
	float Tip = 0.f;
	if (HurtT >= 0.f) Tip = -24.f * FMath::Sin(FMath::Clamp(HurtT / .35f, 0.f, 1.f) * PI);
	const float Spin = PopT < 1.f ? (1.f - PopT) * 90.f : 0.f;
	if (PopT < 1.f) Off += FRotator(0, CurYaw + 90.f, 0).Vector() * (1.f - PopT) * 140.f;
	Pivot->SetRelativeLocation(Off);
	Pivot->SetWorldRotation(FRotator(Tip - FaintK * 80.f, CurYaw + Spin, 0.f));
	Pivot->SetRelativeScale3D(FVector(Pop, Pop, Pop * Breath * (1.f - .06f * Moving * FMath::Abs(FMath::Cos(HopT * 1.6f)))));
	if (MID)
	{
		FlashT = FMath::Max(0.f, FlashT - Dt);
		MID->SetScalarParameterValue(TEXT("Flash"), FlashStrength * FlashT / .35f);
		MID->SetVectorParameterValue(TEXT("FlashColor"), FlashCol);
	}
}
