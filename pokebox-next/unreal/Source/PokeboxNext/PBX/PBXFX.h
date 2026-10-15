// Pokebox Next — lightweight particle effects without Niagara assets: camera-facing glowing sprites drawn with two
// instanced static mesh components (soft dot + star), simulated on the CPU (a few hundred particles at most).
// Used by the battles (hits per Pokémon type, beams, KO puffs, capture sparkles, level-up rings) and for ambient motes.
#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "PBXFX.generated.h"

class UInstancedStaticMeshComponent;

UCLASS()
class APBXFX : public AActor
{
	GENERATED_BODY()
public:
	APBXFX();
	virtual void Tick(float Dt) override;

	/** shape: 0 = soft dot, 1 = star */
	void Burst(const FVector& P, FLinearColor C, int32 N, float Speed, float Size, float Life, float Gravity = -400.f, float UpBias = .4f, uint8 Shape = 0, float Drag = 1.5f);
	/** a hit in the style of the move's Pokémon type (fire embers, water spray, leaves, sparks...) */
	void TypedHit(const FVector& P, const FString& Type, float Power);
	/** particles streaming from A to B for Secs (attack beams / projectiles) */
	void Beam(const FVector& From, const FVector& To, FLinearColor C, float Secs, float Size, uint8 Shape = 0);
	/** expanding ring on the ground (switch-in, level up, guard) */
	void Ring(const FVector& P, FLinearColor C, float Radius, int32 N, float Size = 22.f);
	/** soft rising motes around a box (battle stage atmosphere) */
	void SetAmbient(bool bOn, const FVector& A = FVector::ZeroVector, const FVector& B = FVector::ZeroVector, FLinearColor C = FLinearColor(1, .85f, .5f));
	void Clear();
	/** battle bases (Gen 4-5 platforms): a soft type-tinted disc with a dotted rim lying flat on the ground, slot 0 = yours, 1 = foe */
	void SetBase(int32 Slot, const FVector& P, float Radius, FLinearColor C);
	void ClearBases() { Bases[0].bOn = Bases[1].bOn = false; }

	UPROPERTY(VisibleAnywhere) TObjectPtr<UInstancedStaticMeshComponent> Dots;
	UPROPERTY(VisibleAnywhere) TObjectPtr<UInstancedStaticMeshComponent> Stars;

private:
	struct FP { FVector P, V; FLinearColor C; float Size, Life, Age = 0.f, Grav, Drag, Spin, Rot; uint8 Shape; };
	struct FB { FVector From, To; FLinearColor C; float Secs, T = 0.f, Size, Acc = 0.f; uint8 Shape; };
	TArray<FP> Ps; TArray<FB> Beams;
	struct FBase { bool bOn = false; FVector P = FVector::ZeroVector; float R = 100.f; FLinearColor C = FLinearColor::White; };
	TStaticArray<FBase, 2> Bases;
	bool bAmb = false; FVector AmbA, AmbB; FLinearColor AmbC; float AmbAcc = 0.f;
	void Add(const FP& P) { if (Ps.Num() < 900) Ps.Add(P); }
	void Rebuild();
};
