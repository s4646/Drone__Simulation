import gym
import cv2 
import time
import math
import random
import numpy as np 
from Map import Map
from numba import njit
import PIL.Image as Image
from gym import Env, spaces
from Chopper import Chopper
from itertools import product


font = cv2.FONT_HERSHEY_COMPLEX_SMALL

class ChopperScape(Env):
    def __init__(self, path: str):
        super(ChopperScape, self).__init__()

        self.map = Map(path)
        
        # Define a 2-D observation space
        self.observation_shape = self.map.map.shape # (600, 800, 3)
        self.observation_space = spaces.Box(low = np.zeros(self.observation_shape), 
                                            high = np.ones(self.observation_shape),
                                            dtype = np.float16)
        
        # Define an action space ranging from 0 to 8
        self.action_space = spaces.Discrete(8,)
                        
        # Create a canvas to render the environment images upon 
        self.canvas = np.ones(self.observation_shape) * 1
        
        # Define elements present inside the environment
        self.elements = []
        
        # Maximum fuel chopper can take at once
        self.max_fuel = 4800

        # Permissible area of helicper to be 
        self.y_min = int (self.observation_shape[0] * 0.1)
        self.x_min = 0
        self.y_max = int (self.observation_shape[0] * 0.9)
        self.x_max = self.observation_shape[1]

    def draw_elements_on_canvas(self):
        # Init the canvas 
        # self.canvas = np.ones(self.observation_shape) * 1

        # Draw the heliopter on canvas
        for elem in self.elements:
            elem_shape = elem.icon.shape
            x,y = elem.x, elem.y
            self.canvas[int(y - elem_shape[1]/2) : int(y + elem_shape[1]/2), int(x - elem_shape[0]/2 ): int(x + elem_shape[0]/2)] = elem.rotate_icon()

        text = 'Fuel Left: {} | Rewards: {}'.format(self.fuel_left, self.ep_return)

        # Put the info on canvas 
        self.canvas = cv2.putText(self.canvas, text, (10,20), font,  
                0.8, (255,255,0), 1, cv2.LINE_AA)
        
    @staticmethod
    @njit
    def draw_map_on_canvas(canvas: np.ndarray, map: np.ndarray):
        # Init the canvas 
        canvas = np.ones(map.shape) * 1
        
        h, w, _ = canvas.shape
        for y in range(h):
            for x in range(w):
                canvas[y, x] = map[y, x]
        
        return canvas

    def reset(self, is_train: bool):
        # Reset the fuel consumed
        self.fuel_left = self.max_fuel

        # Reset the reward
        self.total_visited = 0
        self.ep_return  = 0
        self.reward = 0

        self.fuel_count = 0

        # Determine a place to intialise the chopper in
        x = 100
        y = 80
        
        # Intialise the chopper
        self.chopper = Chopper("chopper")
        self.chopper.set_position(y, x)
        self.chopper.create_tips()
        self.chopper.create_sensors()

        # Intialise the elements 
        self.elements = [self.chopper]

        # Reset the Canvas 
        self.canvas = np.ones(self.observation_shape) * 1

        if not is_train:
            # Draw elements on the canvas
            self.canvas = self.draw_map_on_canvas(self.canvas, self.map.map)
            self.draw_elements_on_canvas()

        # return state
        return [0,0,0,0]
    
    def render(self, mode = "human"):
        assert mode in ["human", "rgb_array"], "Invalid mode, must be either \"human\" or \"rgb_array\""
        if mode == "human":
            cv2.imshow("Simulation", self.canvas)
            cv2.waitKey(100)
        
        elif mode == "rgb_array":
            return self.canvas
    
    def close(self):
        cv2.destroyAllWindows()

    def get_action_meanings(self):
        return {0: f"Roll: {1}, Pitch: {1}, Yaw: {5}",
                1: f"Roll: {1}, Pitch: {1}, Yaw: {-5}",
                2: f"Roll: {1}, Pitch: {-1}, Yaw: {5}",
                3: f"Roll: {1}, Pitch: {-1}, Yaw: {-5}",
                4: f"Roll: {-1}, Pitch: {1}, Yaw: {5}",
                5: f"Roll: {-1}, Pitch: {1}, Yaw: {-5}",
                6: f"Roll: {-1}, Pitch: {-1}, Yaw: {5}",
                7: f"Roll: {-1}, Pitch: {-1}, Yaw: {-5}",
                8: f"Roll: {1}, Pitch: {0}, Yaw: {0}",
                9: f"Roll: {-1}, Pitch: {0}, Yaw: {0}",
                10: f"Roll: {0}, Pitch: {1}, Yaw: {0}",
                11: f"Roll: {0}, Pitch: {-1}, Yaw: {0}",
                12: f"Roll: {0}, Pitch: {0}, Yaw: {5}",
                13: f"Roll: {0}, Pitch: {0}, Yaw: {-5}"
                # 14: f"Roll: {0}, Pitch: {0}, Yaw: {0}",
                }

    def has_collided(self):
        tips = self.chopper.tips
        if self.map.is_black(tips[0][0], tips[0][1]): return True
        elif self.map.is_black(tips[1][0], tips[1][1]): return True
        elif self.map.is_black(tips[2][0], tips[2][1]): return True
        elif self.map.is_black(tips[3][0], tips[3][1]): return True
        else: return False

    def step(self, action, is_train: bool):
        # Flag that marks the termination of an episode
        done = False
        
        # Init reward for this step
        self.reward = 0
        
        # Assert that it is a valid action 
        assert self.action_space.contains(action), "Invalid Action"

        # Decrease the fuel counter 
        self.fuel_left -= 1      

        # apply the action to the chopper
        if action == 0:
            self.chopper.move(1, 1, 5)
            self.chopper.create_tips()
            self.chopper.create_sensors()
        elif action == 1:
            self.chopper.move(1, 1, -5)
            self.chopper.create_tips()
            self.chopper.create_sensors()
        elif action == 2:
            self.chopper.move(1, -1, 5)
            self.chopper.create_tips()
            self.chopper.create_sensors()
        elif action == 3:
            self.chopper.move(1, -1, -5)
            self.chopper.create_tips()
            self.chopper.create_sensors()
        elif action == 4:
            self.chopper.move(-1, 1, 5)
            self.chopper.create_tips()
            self.chopper.create_sensors()
        elif action == 5:
            self.chopper.move(-1, 1, -5)
            self.chopper.create_tips()
            self.chopper.create_sensors()
        elif action == 6:
            self.chopper.move(-1, -1, 5)
            self.chopper.create_tips()
            self.chopper.create_sensors()
        elif action == 7:
            self.chopper.move(-1, -1, -5)
            self.chopper.create_tips()
            self.chopper.create_sensors()
        elif action == 8:
            self.chopper.move(1, 0, 0)
            self.chopper.create_tips()
            self.chopper.create_sensors()
        elif action == 9:
            self.chopper.move(-1, 0, 0)
            self.chopper.create_tips()
            self.chopper.create_sensors()
        elif action == 10:
            self.chopper.move(0, 1, 0)
            self.chopper.create_tips()
            self.chopper.create_sensors()
        elif action == 11:
            self.chopper.move(0, -1, 0)
            self.chopper.create_tips()
            self.chopper.create_sensors()
        elif action == 12:
            self.chopper.move(0, 0, 5)
            self.chopper.create_tips()
            self.chopper.create_sensors()
        elif action == 13:
            self.chopper.move(0, 0, -5)
            self.chopper.create_tips()
            self.chopper.create_sensors()
        elif action == 14:
            self.chopper.move(0, 0, 0)
            self.chopper.create_tips()
            self.chopper.create_sensors()
        
        # Print current action
        # print(self.get_action_meanings()[action])

        # Scan area for reward and compute state
        state = self.scan_area()

        if not is_train:
            # Draw elements on the canvas
            self.canvas = self.draw_map_on_canvas(self.canvas, self.map.map)      
            for coord in self.chopper.visited:
                y, x = coord
                x = int(round(x))
                y = int(round(y))
                if not self.map.is_black(y, x): self.canvas[y, x] = [255, 0, 0]
            self.draw_elements_on_canvas()
            for tip in self.chopper.tips:
                y, x = tip
                x = int(round(x))
                y = int(round(y))
                if not self.map.is_black(y, x): self.canvas[y, x] = [0, 0, 255]

        # Reward for executing a step.
        self.reward += len(self.chopper.visited) - self.total_visited - 1
        self.total_visited = len(self.chopper.visited)
        # print(f"total visited: {self.total_visited}, reward: {self.reward}")
        
        # If chopper has collided
        if self.has_collided():
            # Conclude the episode and remove the chopper from the Env.
            done = True
            self.reward = -1000
            self.elements.remove(self.chopper)
        
        # Increment the episodic return
        self.ep_return += self.reward
        # print(f"ep_return: {self.ep_return}")

        # If out of fuel, end the episode.
        if self.fuel_left == 0:
            done = True

        return state, self.reward, done, []

    def scan_area(self):
        ch = self.chopper
        danger_meter = [0, 0, 0, 0] # state of chopper = how close the chopper to a wall
        temp = ch.interpolate_pixels_along_line(ch.sensors[0][0], ch.sensors[0][1], ch.sensors[2][0], ch.sensors[2][1])
        for i, point in enumerate(temp):
            if self.map.is_black(point[0], point[1]):
                # Count danger                
                dist_top = np.sqrt((ch.sensors[0][0] - point[0]) ** 2) + np.sqrt((ch.sensors[0][1] - point[1]) ** 2)
                dist_bottom = np.sqrt((ch.sensors[2][0] - point[0]) ** 2) + np.sqrt((ch.sensors[2][1] - point[1]) ** 2)
                if dist_top < dist_bottom: danger_meter[0] =  0 if danger_meter[0] >= 10 else danger_meter[0]+1
                else: danger_meter[2] =  0 if danger_meter[2] >= 10 else danger_meter[2]+1
                
                # Delete black point from visited
                try: temp = np.delete(temp, i, axis=0)
                except IndexError: continue
                # self.reward -= 1
        
        ch.visited = np.concatenate([ch.visited, temp])

        temp = ch.interpolate_pixels_along_line(ch.sensors[1][0], ch.sensors[1][1], ch.sensors[3][0], ch.sensors[3][1])
        for i, point in enumerate(temp):
            if self.map.is_black(point[0], point[1]):
                # Count danger
                dist_right = np.sqrt((ch.sensors[1][0] - point[0]) ** 2) + np.sqrt((ch.sensors[1][1] - point[1]) ** 2)
                dist_left = np.sqrt((ch.sensors[3][0] - point[0]) ** 2) + np.sqrt((ch.sensors[3][1] - point[1]) ** 2)
                if dist_right < dist_left: danger_meter[1] = 0 if danger_meter[1] >= 10 else danger_meter[1]+1
                else: danger_meter[3] = 0 if danger_meter[3] >= 10 else danger_meter[3]+1

                # Delete black point from visited
                try: temp = np.delete(temp, i, axis=0)
                except IndexError: continue
                # self.reward -= 1

        ch.visited = np.concatenate([ch.visited, temp])

        ch.visited = np.unique(ch.visited, axis=0)
        
        return danger_meter


def train(env: ChopperScape):

    # Initialize Q-table with zeros
    options = list(product(range(0, 11), repeat=4))
    num_states = len(options)
    num_actions = env.action_space.n
    Q = np.zeros((num_states, num_actions))

    # Hyperparameters
    alpha = 0.15 # Learning rate
    gamma = 0.99  # Discount factor
    epsilon = 0.5  # Exploration rate

    # Training loop
    num_episodes = 1000
    for episode in range(num_episodes):
        state = env.reset(True)
        total_reward = 0
        done = False

        while not done:
            # Choose action based on epsilon-greedy policy
            if np.random.rand() < epsilon:
                action = env.action_space.sample()  # Explore
            else:
                action = np.argmax(Q[options.index(tuple(state)), :])  # Exploit

            next_state, reward, done, _ = env.step(action, True)

            # Update Q-value using Q-learning update rule
            Q[options.index(tuple(state)), action] += alpha * \
            (reward + gamma * np.max(Q[options.index(tuple(next_state))]) - Q[options.index(tuple(state)), action])

            state = next_state
            total_reward += reward
        
        print(f"Epoch: {episode}, Total Reward: {total_reward}")
    
    print("Agent training complete!")
    return Q

def main():
    path_to_map = "pictures/maps/p11.png"

    env = ChopperScape(path_to_map)

    Q = train(env)
    np.save('Q',Q)
    Q = np.load('Q.npy')
    options = list(product(range(0, 11), repeat=4))

    for _ in range(10):

        state = env.reset(False)

        while True:
            # Take an action
            action = np.argmax(Q[options.index(tuple(state)), :])
            # action = env.action_space.sample()
            state, reward, done, info = env.step(action, False)
            # print(state)
            
            # Render the game
            env.render(mode='human')
            env.canvas = np.ones(env.observation_shape) * 1
            
            if done == True:
                break

    env.close()
if __name__ == "__main__":
    main()