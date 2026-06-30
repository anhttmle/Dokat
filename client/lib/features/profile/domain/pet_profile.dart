/// Pet profile data.
class PetProfile {
  const PetProfile({
    required this.petId,
    required this.name,
    required this.species,
    this.avatarUrl,
    this.linkedPhotoUrl,
  });

  final String petId;
  final String name;

  /// 'dog' or 'cat'.
  final String species;
  final String? avatarUrl;

  /// CDN URL of the most recently linked post photo.
  /// Populated only when backend adds this field.
  final String? linkedPhotoUrl;

  factory PetProfile.fromJson(Map<String, dynamic> json) {
    return PetProfile(
      petId: json['id'] as String,
      name: json['name'] as String,
      species: json['species'] as String,
      avatarUrl: json['avatar_url'] as String?,
      linkedPhotoUrl: json['linked_photo_url'] as String?,
    );
  }

  Map<String, dynamic> toJson() => {
        'name': name,
        'species': species,
      };

  PetProfile copyWith({
    String? name,
    String? species,
    String? avatarUrl,
    String? linkedPhotoUrl,
  }) {
    return PetProfile(
      petId: petId,
      name: name ?? this.name,
      species: species ?? this.species,
      avatarUrl: avatarUrl ?? this.avatarUrl,
      linkedPhotoUrl: linkedPhotoUrl ?? this.linkedPhotoUrl,
    );
  }
}
