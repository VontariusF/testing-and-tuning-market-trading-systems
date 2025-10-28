#include "strategy.h"
#include <vector>
#include <string>

class MACrossoverStrategy : public Strategy {
public:
    MACrossoverStrategy(int fast_period, int slow_period)
        : fast_period_(fast_period), slow_period_(slow_period) {
        if (fast_period_ >= slow_period_) {
            fast_period_ = 10;
            slow_period_ = 50;
        }
    }

    void on_start() override {
        closes_.clear();
        position_ = 0;
        trades_ = 0;
    }

    void on_bar(const Bar& b) override {
        double price = b.close;
        closes_.push_back(price);

        if (closes_.size() < (size_t)slow_period_) {
            return;
        }

        // Calculate moving averages
        double fast_sum = 0.0, slow_sum = 0.0;
        for (int i = 0; i < fast_period_; ++i) {
            fast_sum += closes_[closes_.size() - 1 - i];
        }
        for (int i = 0; i < slow_period_; ++i) {
            slow_sum += closes_[closes_.size() - 1 - i];
        }

        double fast_ma = fast_sum / fast_period_;
        double slow_ma = slow_sum / slow_period_;

        // Generate signals
        int desired_position = 0;
        if (fast_ma > slow_ma) {
            desired_position = 1;  // Long
        } else if (fast_ma < slow_ma) {
            desired_position = -1; // Short
        }

        // Execute trades
        if (desired_position != position_) {
            position_ = desired_position;
            ++trades_;
        }
    }

    void on_finish() override {
        printf("MA Crossover Strategy: Fast=%d, Slow=%d, Trades=%d\n",
               fast_period_, slow_period_, trades_);
    }

private:
    int fast_period_;
    int slow_period_;
    std::vector<double> closes_;
    int position_ = 0;
    int trades_ = 0;
};

// Factory function
Strategy* make_ma_crossover_strategy() {
    return new MACrossoverStrategy(10, 50);
}
