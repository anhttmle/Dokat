if(NOT TARGET hermes-engine::libhermes)
add_library(hermes-engine::libhermes SHARED IMPORTED)
set_target_properties(hermes-engine::libhermes PROPERTIES
    IMPORTED_LOCATION "/Users/anhttmle1/.gradle/caches/8.10.2/transforms/4e94eecaac2a27f40493b37f065ada37/transformed/hermes-android-0.76.9-debug/prefab/modules/libhermes/libs/android.x86_64/libhermes.so"
    INTERFACE_INCLUDE_DIRECTORIES "/Users/anhttmle1/.gradle/caches/8.10.2/transforms/4e94eecaac2a27f40493b37f065ada37/transformed/hermes-android-0.76.9-debug/prefab/modules/libhermes/include"
    INTERFACE_LINK_LIBRARIES ""
)
endif()

