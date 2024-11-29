#include <flecs.h>
#include <iostream>
#include <vector>

// The Construction of the Advice Taker
// http://www-formal.stanford.edu/jmc/mcc59/node2.html

struct Person { };
struct Furniture { };
struct Vehicle { };
struct Room { };
struct Building { };
struct Facility { };
struct Country { };

struct At {};
struct In {};

struct Walkable {};
struct Drivable {};

struct Can {};
struct Did 
{
    flecs::id y;
    flecs::id z;
    std::string action;
    friend std::ostream& operator<<(std::ostream& os, const Did& obj) {
        os << "go from " << obj.y.second().name() << " to " << obj.z.second().name() << " " << obj.action;
        return os;
    }
};

struct Go 
{
    flecs::id y;
    flecs::id z;
    std::string action;
    friend std::ostream& operator<<(std::ostream& os, const Go& obj) {
        os << "go from " << obj.y.second().name() << " to " << obj.z.second().name() << " " << obj.action;
        return os;
    }
};

struct Action
{
    flecs::entity source;
    Go go;
};

void generate_possible_actions(flecs::world& ecs, flecs::entity& I, flecs::entity& car, flecs::entity& WalkAction, flecs::entity& DriveAction)
{
    // walkable(x), at(y, x), at(z, x), at(I, y) → can(go(y, z, walking))
    flecs::query<> q_walk = ecs.query_builder()
        .with<At>("$location")
        .with<Walkable>().src("$location")
        .build();

    int location_var = q_walk.find_var("location");

    q_walk.each([&](flecs::iter& it, size_t index) {
        if (it.entity(index) != I)
        {
            // This needs to be more specific
            auto where_I_am = I.target<At>();

            flecs::entity a_place = it.entity(index);
            flecs::entity walk_action = ecs.entity().is_a(WalkAction);
            if (where_I_am != a_place)
            {
                walk_action.set<Go>({where_I_am, a_place, "by walking"});
                I.add<Can>(walk_action);
            }
        }
    });

    flecs::query<> q_drive = ecs.query_builder()
        .with<At>("$location")
        .with<Drivable>().src("$location")
        .with<Building>() // because of Transitivity of At, we need to further specify query 
        .build();

    int drive_location_var = q_drive.find_var("location");

    q_drive.each([&](flecs::iter& it, size_t index) {
        if (it.entity(index) != car)
        {
            auto where_car_is = it.get_var(drive_location_var);
            flecs::entity a_place = it.entity(index);
            flecs::entity drive_action = ecs.entity().is_a(DriveAction);
            if (where_car_is != a_place) // We need to *transitively* query if car is already at this place!
            {
                drive_action.set<Go>({where_car_is, a_place, "by driving"});
                car.add<Can>(drive_action);
            }
        }
    });
}

void remove_possible_actions(flecs::world& ecs)
{
    flecs::query<> possible_actions_query = ecs.query_builder()
        .with<Can>(flecs::Wildcard) // Query all entities with the Can relationship
        .build();

    ecs.defer_begin();
    possible_actions_query.each([&](flecs::iter& it, size_t i) {
        auto entity = it.entity(i);
        entity.remove<Can>(flecs::Wildcard);
    });
    ecs.defer_end();
}

int main(int, char*[]) {
    flecs::world ecs;

    flecs::entity Vehicle = ecs.prefab("Vehicle");
    // flecs::entity Driver = ecs.prefab("Driver")
    //     .child_of(Vehicle)
    //     .slot_of(Vehicle);

    flecs::entity I = ecs.entity("John McCarthy").add<Person>();
    flecs::entity desk = ecs.entity("desk").add<Furniture>();
    flecs::entity garage = ecs.entity("garage").add<Room>();
    flecs::entity car = ecs.entity("car").is_a(Vehicle);
    flecs::entity office = ecs.entity("office").add<Room>();
    flecs::entity home = ecs.entity("885 Allardice Way").add<Building>();
    flecs::entity airport = ecs.entity("San Francisco International Airport").add<Building>();
    flecs::entity country = ecs.entity("United States").add<Country>();

    flecs::entity WalkAction = ecs.prefab("WalkAction");
    flecs::entity DriveAction = ecs.prefab("DriveAction");

    ecs.component<At>().add(flecs::Transitive);
    ecs.component<Walkable>().add(flecs::Transitive); // Transitivity scope and conditionality
    // (ie you cannot walk to certain regions inside a home)
    // this is where logical navigation is enacted with realtime pathfinding

    // ecs.component<Drivable>().add(flecs::Transitive); // Consider something like a 'transitivity interrupt'

    // Initialize the default world state

    // There are two rules concerning the feasibility of walking and driving.
    country.add<Drivable>();
    home.add<Walkable>();

    // I am seated at my desk
    I.add<At>(home);

    // Desk at home
    desk.add<At>(office);
    office.add<At>(home);

    // Car at home
    car.add<At>(home);
    garage.add<At>(home);

    // Home in country
    home.add<At>(country);
    // Airport in country
    airport.add<At>(country);

    // Create the actions which can be taken, given an ECS world
    generate_possible_actions(ecs, I, car, WalkAction, DriveAction);
    //remove_possible_actions(ecs);

    // There is an immediate deduction routine which when given a set of premises (flecs::world ecs) 
    // will deduce a set of immediate conclusions.
    flecs::query<> deduction_query = ecs.query_builder()
        .with<Can>("$action")
        .build();

    int action_var = deduction_query.find_var("action");

    // First, we query to collect the immediate conclusions
    std::vector<Action> open_set_nodes;
    deduction_query.each([&](flecs::iter& it, size_t index) {
        Go diff = it.get_var(action_var).get_mut<Go>()[0];
        std::cout << "Immediate Conclusion: " << it.entity(index).name() << " can " << diff << std::endl;
        
        open_set_nodes.push_back({it.entity(index), diff});
    });

    for (auto& action : open_set_nodes)
    {
        // LOG actions that occured
        std::cout << action.source.name() << " navigated " << action.go.y.second().name() << " to " << action.go.z.second().name() << std::endl;

        flecs::string json = ecs.to_json();
        std::cout << json << std::endl;

        // These are the 'ramifications'
        I.set<Did>({action.go.y, action.go.z, action.go.action});
        
        action.source.remove<At>(action.go.y);
        action.source.add<At>(action.go.z);
        // TODO: Act out

        // ---- PATHFINDING OBJECTIVE ---- 
        // In the ECS world of each immediate conclusion, we may run some query to determine if the conditions of
        // our objective are met, and perhaps even consider side effects...
        flecs::query<> objective_query = ecs.query_builder()
            .with<At>("$location").src(I)
            .build();

        int objective_var = objective_query.find_var("location");
        bool objective_state_reached = false;

        objective_query.each([&](flecs::iter& it, size_t index) {
            std::cout << "John McCarthy is at " << it.get_var(action_var).name() << std::endl;
            // John McCarthy is at the airport
            if (it.get_var(action_var) == airport)
            {
                objective_state_reached = true;
            }
        });
        std::cout << "Objective reached: " << objective_state_reached << std::endl;
        // -----------------------------------

        flecs::world world_b;
        world_b.from_json(json);
        remove_possible_actions(world_b);
        // generate_possible_actions

        // If the objective is reached, we should backtrack to find the 'path of actions'
        // Otherwise, we should store the world at the state after the action was taken (to be restored later)
        // These states form nodes, and we can perform a simple breadth first search
        //ecs_world_from_json(world_b, json, NULL);
        // TODO: Snapshot the entire ECS world to account for observers and side effects being tracked...

        action.source.remove<At>(action.go.z);
        action.source.add<At>(action.go.y);

    }
}