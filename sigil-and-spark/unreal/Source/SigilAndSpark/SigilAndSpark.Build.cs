// Copyright Epic Games, Inc. All Rights Reserved.

using UnrealBuildTool;

public class SigilAndSpark : ModuleRules
{
	public SigilAndSpark(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

		PublicDependencyModuleNames.AddRange(new string[] {
			"Core",
			"CoreUObject",
			"Engine",
			"InputCore",
			"EnhancedInput",
			"AIModule",
			"StateTreeModule",
			"GameplayStateTreeModule",
			"UMG",
			"Slate",
			"SlateCore",
			"Json",
			"JsonUtilities",
			"AssetRegistry",
			"HairStrandsCore",
			"MediaAssets",
			"Media",
			"AudioMixer"
		});

		PrivateDependencyModuleNames.AddRange(new string[] { });

		PublicIncludePaths.AddRange(new string[] {
			"SigilAndSpark",
			"SigilAndSpark/PBX",
			"SigilAndSpark/Variant_Platforming",
			"SigilAndSpark/Variant_Platforming/Animation",
			"SigilAndSpark/Variant_Combat",
			"SigilAndSpark/Variant_Combat/AI",
			"SigilAndSpark/Variant_Combat/Animation",
			"SigilAndSpark/Variant_Combat/Gameplay",
			"SigilAndSpark/Variant_Combat/Interfaces",
			"SigilAndSpark/Variant_Combat/UI",
			"SigilAndSpark/Variant_SideScrolling",
			"SigilAndSpark/Variant_SideScrolling/AI",
			"SigilAndSpark/Variant_SideScrolling/Gameplay",
			"SigilAndSpark/Variant_SideScrolling/Interfaces",
			"SigilAndSpark/Variant_SideScrolling/UI"
		});

		// Uncomment if you are using Slate UI
		// PrivateDependencyModuleNames.AddRange(new string[] { "Slate", "SlateCore" });

		// Uncomment if you are using online features
		// PrivateDependencyModuleNames.Add("OnlineSubsystem");

		// To include OnlineSubsystemSteam, add it to the plugins section in your uproject file with the Enabled attribute set to true
	}
}
