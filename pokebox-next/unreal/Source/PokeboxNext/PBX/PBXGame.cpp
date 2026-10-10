#include "PBX/PBXGame.h"
#include "Kismet/GameplayStatics.h"

void UPBXGameSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);
	State = NewObject<UPBXSaveGame>(this);
}

void UPBXGameSubsystem::NewGame(bool bMale)
{
	State = NewObject<UPBXSaveGame>(this);
	State->bMale = bMale;
}

bool UPBXGameSubsystem::HasSave() const { return UGameplayStatics::DoesSaveGameExist(Slot, 0); }

bool UPBXGameSubsystem::Save(const FVector& Pos, float Yaw)
{
	if (!State) return false;
	State->Pos = Pos; State->Yaw = Yaw; State->bHasPos = true; State->SavedAt = FDateTime::Now().ToString(TEXT("%Y-%m-%d %H:%M"));
	return UGameplayStatics::SaveGameToSlot(State, Slot, 0);
}

bool UPBXGameSubsystem::Load()
{
	if (!HasSave()) return false;
	if (UPBXSaveGame* S = Cast<UPBXSaveGame>(UGameplayStatics::LoadGameFromSlot(Slot, 0))) { State = S; return true; }
	return false;
}

void UPBXGameSubsystem::HealAll()
{
	if (!State) return;
	for (FPBXMon& M : State->Team) M.HP = -1;
	for (FPBXMon& M : State->Box) M.HP = -1;
}

bool UPBXGameSubsystem::AddMon(FName Card, int32 Lv)
{
	FPBXMon M; M.Card = Card; M.Lv = Lv; State->Seen.AddUnique(Card);
	if (State->Team.Num() < TeamMax) { State->Team.Add(M); return true; }
	State->Box.Add(M); return false;
}
