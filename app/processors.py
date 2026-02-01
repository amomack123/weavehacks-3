"""
Custom Pipecat Frame Processors
Implements behavioral reward processing and action coordination
"""

import logging
from typing import Optional

from pipecat.frames.frames import Frame
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from .logging_utils import conversation_logger

logger = logging.getLogger(__name__)

# ============================================
# CUSTOM ACTION FRAMES
# ============================================

class ActionFrame(Frame):
    """Frame carrying coordinate-based action instructions for Electron"""
    def __init__(self, action: str, start_pos: dict, end_pos: dict, metadata: Optional[dict] = None):
        super().__init__()
        self.action = action
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.metadata = metadata or {}

class ActionFeedbackFrame(Frame):
    """Frame carrying feedback from Electron about an action success"""
    def __init__(self, action_id: str, success: bool, user_delta: float, metadata: Optional[dict] = None):
        super().__init__()
        self.action_id = action_id
        self.success = success
        self.user_delta = user_delta
        self.metadata = metadata or {}

# ============================================
class RewardProcessor(FrameProcessor):
    """
    Observes ActionFeedbackFrames and updates the reward store.
    This acts as the Behavioral Learning hook in the pipeline.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    async def process_frame(self, frame: Frame, direction: FrameDirection):
        """Process incoming frames to detect feedback and update rewards"""
        
        # Let parent class handle StartFrame and other lifecycle frames first
        from pipecat.frames.frames import StartFrame, EndFrame, CancelFrame
        if isinstance(frame, (StartFrame, EndFrame, CancelFrame)):
            await super().process_frame(frame, direction)
            return
        
        # Process ActionFeedbackFrame if applicable
        if isinstance(frame, ActionFeedbackFrame):
            logger.info(f"Received feedback for action {frame.action_id}: success={frame.success}")
            
            # Calculate reward based on success and user delta (distance to target)
            reward = 1.0 if frame.success and frame.user_delta < 50 else -1.0
            
            # Update Episodic Memory / Reward Store
            await self._update_reward_store(frame.action_id, reward, frame.metadata)
            
            # Log event for analytics
            conversation_logger.log_event("reward_update", {
                "action_id": frame.action_id,
                "reward": reward,
                "delta": frame.user_delta
            })
        
        # Pass all frames downstream
        await self.push_frame(frame, direction)

    # async def _update_reward_store(self, action_id: str, reward: float, metadata: dict):
    #     """
    #     Internal hook to update the permanent reward store
    #     In production, this would involve updating the specific Q-value 
    #     or weights associated with the (screen_state, action) pair in Redis.
    #     """
    #     logger.debug(f"Reward store update: {action_id} -> {reward}")
        # : Implement Redis Reward update logic
    #     pass

    async def _update_reward_store(self, action_id: str, reward: float, metadata: dict):
        """
        Updates the Redis-style Episodic Memory.
        The RL logic uses a composite key of (Screen + Intent) to store mask success.
        """
        screen_hash = metadata.get("screen_state_hash")  # The 'State'
        intent = metadata.get("user_intent")            # The 'Action'
        mask_id = metadata.get("sam_mask_id")           # The 'Specific Actuator'
        
        if not (screen_hash and intent and mask_id):
            logger.warning(f"Missing RL metadata for action {action_id}")
            return

        # THE REDIS SCHEMA: Key = Context, Field = Mask, Value = Cumulative Reward
        # Format: rewards:{screen_state_hash}:{user_intent}
        rl_key = f"rewards:{screen_hash}:{intent}"
        
        # In production: redis.hincrbyfloat(rl_key, mask_id, reward)
        logger.info(f"RL PERSIST: Key='{rl_key}', Mask='{mask_id}', Reward={reward}")