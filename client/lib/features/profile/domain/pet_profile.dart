/// Pet profile data.
class PetProfile {
  const PetProfile({
    required this.petId,
    required this.name,
    required this.species,
    this.breed,
    this.avatarUrl,
    this.linkedPhotoUrl,
  });

  final String petId;
  final String name;

  /// 'dog' or 'cat'.
  final String species;
  final String? breed;
  final String? avatarUrl;
  final String? linkedPhotoUrl;

  factory PetProfile.fromJson(Map<String, dynamic> json) {
    return PetProfile(
      petId: json['pet_id'] as String,
      name: json['name'] as String,
      species: json['species'] as String,
      breed: json['breed'] as String?,
      avatarUrl: json['avatar_url'] as String?,
      linkedPhotoUrl: json['linked_photo_url'] as String?,
    );
  }

  Map<String, dynamic> toJson() => {
        'name': name,
        'species': species,
        if (breed != null) 'breed': breed,
      };

  PetProfile copyWith({
    String? name,
    String? species,
    String? breed,
    String? avatarUrl,
    String? linkedPhotoUrl,
  }) {
    return PetProfile(
      petId: petId,
      name: name ?? this.name,
      species: species ?? this.species,
      breed: breed ?? this.breed,
      avatarUrl: avatarUrl ?? this.avatarUrl,
      linkedPhotoUrl: linkedPhotoUrl ?? this.linkedPhotoUrl,
    );
  }
}
