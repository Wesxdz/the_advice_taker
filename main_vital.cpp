#include <flecs.h>
#include <iostream>
#include <fstream>
#include <string>

#include <vital_module.h>

int main(int argc, char *argv[])
{
    flecs::world world;

    ECS_IMPORT(world, VitalModule);

    ecs_query_desc_t query_desc = {
        // Next step: COM_Specific_video_games_and_series 'MadeIn' COM_Japan
        .terms = {
            // COM_History_of_video_games Note that querying categories does not give expected results
            // TODO: Investigate COM_History_of_video_games
            { .id = ecs_id(COM_Science_and_Engineering) } // Specify the component to query
        }
    };

    // Create the query
    ecs_query_t *q = ecs_query_init(world, &query_desc);
    if (!q) {
        printf("Failed to create query\n");
        return -1;
    }

    printf("Entities with :\n");
    ecs_iter_t it = ecs_query_iter(world, q);
    while (ecs_query_next(&it)) {
        for (int i = 0; i < it.count; i++) {
            const char *name = ecs_get_name(world, it.entities[i]);
            printf("  - %s\n", name ? name : "Unnamed Entity");
        }
    }
    ecs_progress(world, 1.0);
}