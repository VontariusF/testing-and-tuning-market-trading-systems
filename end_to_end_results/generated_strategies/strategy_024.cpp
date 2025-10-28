#include "strategy.h"
#include <vector>
#include <string>

class RSIStrategy : public Strategy {
public:
    RSIStrategy(int period, double overbought, double oversold)
        : period_(period), overbought_(overbought), oversold_(oversold) {
    }

    void on_start() override {
        closes_.clear();
        gains_.clear();
        losses_.clear();
        position_ = 0;
        trades_ = 0;
    }

    void on_bar(const Bar& b) override {
        double price = b.close;
        closes_.push_back(price);

        if (closes_.size() < 2) return;

        // Calculate gains and losses
        double change = price - closes_[closes_.size() - 2];
        gains_.push_back(change > 0 ? change : 0);
        losses_.push_back(change < 0 ? -change : 0);

        if (gains_.size() < (size_t)period_) return;

        // Calculate RSI
        double avg_gain = 0.0, avg_loss = 0.0;
        for (int i = gains_.size() - period_; i < gains_.size(); ++i) {
            avg_gain += gains_[i];
            avg_loss += losses_[i];
        }
        avg_gain /= period_;
        avg_loss /= period_;

        double rs = avg_loss != 0 ? avg_gain / avg_loss : 0;
        double rsi = 100.0 - (100.0 / (1.0 + rs));

        // Generate signals
        int desired_position = 0;
        if (rsi < oversold_) {
            desired_position = 1;  // Long
        } else if (rsi > overbought_) {
            desired_position = -1; // Short
        }

        // Execute trades
        if (desired_position != position_) {
            position_ = desired_position;
            ++trades_;
        }
    }

    void on_finish() override {
        printf("RSI Strategy: Period=%d, OB=%g, OS=%g, Trades=%d\n",
               period_, overbought_, oversold_, trades_);
    }

private:
    int period_;
    double overbought_;
    double oversold_;
    std::vector<double> closes_;
    std::vector<double> gains_;
    std::vector<double> losses_;
    int position_ = 0;
    int trades_ = 0;
};

// Factory function
Strategy* make_rsi_strategy() {
    return new RSIStrategy(14, 70, 30);
}
