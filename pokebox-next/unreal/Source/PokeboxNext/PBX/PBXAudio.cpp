#include "PBX/PBXAudio.h"
#include "Sound/SoundWaveProcedural.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

namespace
{
	struct FPCM { TArray<uint8> Data; int32 Rate = 24000, Channels = 1; float Seconds = 0.f; };
	TMap<FString, TSharedPtr<FPCM>> GCache;

	TSharedPtr<FPCM> Parse(const FString& File)
	{
		TArray<uint8> B;
		if (!FFileHelper::LoadFileToArray(B, *File) || B.Num() < 44 || FMemory::Memcmp(B.GetData(), "RIFF", 4) || FMemory::Memcmp(B.GetData() + 8, "WAVE", 4)) return nullptr;
		TSharedPtr<FPCM> P = MakeShared<FPCM>(); int32 Bits = 16, Fmt = 1; int32 i = 12;
		auto U16 = [&](int32 o) { return int32(B[o] | (B[o + 1] << 8)); };
		auto U32 = [&](int32 o) { return int32(B[o] | (B[o + 1] << 8) | (B[o + 2] << 16) | (B[o + 3] << 24)); };
		while (i + 8 <= B.Num())
		{
			const int32 Sz = U32(i + 4); const uint8* Id = B.GetData() + i;
			if (!FMemory::Memcmp(Id, "fmt ", 4)) { Fmt = U16(i + 8); P->Channels = U16(i + 10); P->Rate = U32(i + 12); Bits = U16(i + 22); }
			else if (!FMemory::Memcmp(Id, "data", 4)) { const int32 N = FMath::Min(Sz, B.Num() - (i + 8)); P->Data.Append(B.GetData() + i + 8, N); }
			i += 8 + Sz + (Sz & 1);
		}
		if (Fmt != 1 || Bits != 16 || P->Channels < 1 || P->Channels > 2 || !P->Data.Num()) { UE_LOG(LogTemp, Warning, TEXT("[PBXAUDIO] %s: need 16-bit PCM mono/stereo"), *File); return nullptr; }
		P->Seconds = float(P->Data.Num()) / (2.f * P->Channels * P->Rate);
		return P;
	}
}

FString PBXAudio::Path(const TCHAR* Kind, const FString& Name) { return FPaths::ProjectContentDir() / TEXT("PBX/StoryAudio") / Kind / (Name + TEXT(".wav")); }
bool PBXAudio::Exists(const TCHAR* Kind, const FString& Name) { return !Name.IsEmpty() && FPaths::FileExists(Path(Kind, Name)); }

USoundWaveProcedural* PBXAudio::Load(UObject* Outer, const TCHAR* Kind, const FString& Name, bool bLoop, float* OutSeconds)
{
	const FString File = Path(Kind, Name);
	TSharedPtr<FPCM> P = GCache.FindRef(File);
	if (!P.IsValid()) { P = Parse(File); if (!P.IsValid()) return nullptr; GCache.Add(File, P); }
	USoundWaveProcedural* W = NewObject<USoundWaveProcedural>(Outer);
	W->SetSampleRate(P->Rate); W->NumChannels = P->Channels; W->SoundGroup = SOUNDGROUP_Default;
	W->Duration = bLoop ? INDEFINITELY_LOOPING_DURATION : P->Seconds; W->bLooping = false;
	W->QueueAudio(P->Data.GetData(), P->Data.Num());
	if (bLoop)
	{
		TWeakPtr<FPCM> WP = P;
		W->OnSoundWaveProceduralUnderflow.BindLambda([WP](USoundWaveProcedural* S, int32 /*Samples*/)
		{
			if (TSharedPtr<FPCM> Q = WP.Pin()) if (S->GetAvailableAudioByteCount() < Q->Rate * Q->Channels * 2) S->QueueAudio(Q->Data.GetData(), Q->Data.Num());
		});
	}
	if (OutSeconds) *OutSeconds = P->Seconds;
	return W;
}
