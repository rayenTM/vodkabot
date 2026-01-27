def calculate_xp_requirement(level: int) -> int:
    """
    Calculates the TOTAL XP required to reach a specific level.
    Formula: 100 * (Level - 1)^2
    """
    return 100 * ((level - 1) ** 2)

print(f"{'Level':<10} | {'Total XP Required':<20} | {'Delta from Prev':<15}")
print("-" * 50)

previous_xp = 0
for level in range(1, 21):
    xp = calculate_xp_requirement(level)
    delta = xp - previous_xp
    print(f"{level:<10} | {xp:<20} | {delta:<15}")
    previous_xp = xp
